#!/usr/bin/env python

import argparse, os, sys, subprocess, re, json

cache = {}
# cache = {
#   name : {
#     'path' : str,
#     'validated' : dict,
#     'built' : dict,
#     'pushed' : bool
#   },
#   ...
# }

def run_shell_cmd(path, cmd):
  out, err = subprocess.Popen(
    cmd.split(), cwd=path, stdout=subprocess.PIPE, stderr=subprocess.PIPE
  ).communicate()
  if err:
    sys.exit("Error running command: '%s' at '%s'\n%s" % (cmd, path, err))
  return out

def load_package_info(path):
  try:
    with open(os.path.join(path, "package.json"), 'r') as infile:
      return json.load(infile)
  except:
    return None

def get_version_info(package_info):
  pattern = r"^(?P<major>[0-9]+)\.(?P<minor>[0-9]+)\.(?P<build>[0-9]+)$"
  match = re.match(pattern, package_info['version'])
  return match.groupdict() if match else None

def is_chroma_repository(url):
  is_bitbucket = bool(re.match(r".*bitbucket\.org/chromawallet.*", url))
  is_github = bool(re.match(r".*github\.com/chromaway.*", url))
  return is_bitbucket or is_github

def get_chroma_dependencie_paths(path, package_info):
  items = package_info["dependencies"].items()
  items = filter(lambda item: is_chroma_repository(item[1]), items)
  names = map(lambda item: item[0], items)
  return map(lambda name: os.path.join(path, 'node_modules', name), names)


############
# validate #
############

def validate_command(path):
  # validate root -> leaves
  validated = validate_repository(path)
  paths = get_chroma_dependencie_paths(path, validated['package_info'])
  map(validate_command, paths)

def validate_repository(path, remote=None):
  global cache
  path = os.path.realpath(path)
  if not is_git_repository(path):
    sys.exit("No git repository for package '%s'!" % path)
  if remote:
    pass # TODO validate can push to remote using ssh key
  if has_uncommitted_changes(path):
    sys.exit("Uncommitted changes for package '%s'!" % path)
  if not on_development_branch(path):
    sys.exit("Not on 'development' branch for package '%s'!" % path)
  # TODO master must be on last tagged build
  # TODO development branch must include all master commits
  package_info = load_package_info(path)
  if not package_info:
    sys.exit("Could not load package data for '%s'!" % path)
  name = package_info['name']
  if name in cache:
    other_path = cache[name]['path']
    if path != other_path:
      sys.exit("Duplicate paths for %s: %s and %s" % (name, path, other_path))
    return cache[name]['validated']
  version_info = get_version_info(package_info)
  if not bool(version_info):
    sys.exit("No version key for package '%s'!" % path)
  if not ('repository' in package_info and 'url' in package_info["repository"]):
    sys.exit("No repository.url for package '%s'!" % path)
  if not is_chroma_repository(package_info["repository"]["url"]):
    sys.exit("Package '%s' not a chroma repository!" % path)
  if not last_tagged_version_matches_package(path, version_info):
    sys.exit("Last tagged version does not match package for '%s'!" % path)
  # TODO validate all required dependencies installed
  # TODO all unittests must pass
  init_cache(path, name, package_info, version_info)
  print "Validated: %s" % name
  return cache[name]['validated']

def init_cache(path, name, package_info, version_info):
  global cache
  cache[name] = {
    'path' : path, 'built' : None, 'pushed' : None,
    'validated' : {
      'package_info' : package_info, 'version_info' : version_info
    }
  }

def last_tagged_version_matches_package(path, version_info):
  last_tagged = run_shell_cmd(path, 'git describe --tags')
  pattern = r"^v%(major)s\.%(minor)s\.%(build)s" % version_info
  return bool(re.match(pattern, last_tagged))

def on_development_branch(path):
  out = run_shell_cmd(path, "git branch")
  is_development = lambda x: re.match(r"^\* development$", x)
  return bool(filter(is_development, out.split('\n')))

def has_uncommitted_changes(path):
  return bool(run_shell_cmd(path, 'git status --porcelain'))

def is_git_repository(path):
  return os.path.isdir(os.path.join(path, ".git"))


########
# push #
########

def push_command(path, remote):
  global cache
  path = os.path.realpath(path)
  validate_command(path) # validate everything before pushing

  # push dependencies first
  package_info = load_package_info(path)
  paths = get_chroma_dependencie_paths(path, package_info)
  map(lambda p: push_command(p, remote), paths)

  # chack if already pushed
  if cache[package_info['name']]['pushed']:
    return

  # push master and development branches as well as tags
  print "Pushing: %s -> %s" % (package_info['name'], remote)
  run_shell_cmd(path, 'git push --quiet %s master' % remote)
  run_shell_cmd(path, 'git push --quiet %s development' % remote)
  run_shell_cmd(path, 'git push --quiet --tags %s ' % remote)
  cache[package_info['name']]['pushed'] = True


#########
# build #
#########

def build_command(path):
  validate_command(path) # validate everything before building
  build_repository(path) # build leaves -> root

def build_repository(path):

  # chack if already built
  global cache
  path = os.path.realpath(path)
  package_info = load_package_info(path)
  if cache[package_info['name']]['built']:
    return cache[package_info['name']]['built']

  # build dependencies first
  paths = get_chroma_dependencie_paths(path, package_info)
  dependencies_built = map(build_repository, paths)

  # build package
  updated = False
  dependencies_changed = dependencies_updated(dependencies_built)
  repository_changed = not is_head_at_verison(path, package_info['version'])
  print "Building:", package_info['name']
  if dependencies_changed or repository_changed:
    dependencies = map(lambda x: x['package_info'], dependencies_built)
    update_dependencie_info(package_info, dependencies)
    increment_build_version(package_info)
    save_package_info(path, package_info)
    merge_and_tag_build(path, package_info['version'])
    updated = True
  else:
    print "  unchanged %s" % package_info['version']
  cache[package_info['name']]['built'] = {
    "package_info" : package_info, "updated" : updated
  }
  return cache[package_info['name']]['built']

def update_dependencie_info(package_info, dependencies):
  for dependencie_info in dependencies:
    base_url = dependencie_info["repository"]["url"]
    new_url = base_url + "#v" + dependencie_info["version"]
    package_info["dependencies"][dependencie_info["name"]] = new_url

def increment_build_version(package_info):
  version_info = get_version_info(package_info)
  old = package_info["version"]
  version_info["build"] = str(int(version_info["build"]) + 1)
  package_info["version"] = "%(major)s.%(minor)s.%(build)s" % version_info
  new = package_info["version"]
  print "  updating %s -> %s" % (old, new)

def is_head_at_verison(path, version):
  head_commit = run_shell_cmd(path, "git rev-parse --verify HEAD")
  tag_commit = run_shell_cmd(path, "git rev-list -1 v%s" % version)
  if not head_commit:
    raise Exception("Couldn't get head commit id!")
  if not tag_commit:
    raise Exception("Couldn't get tag commit id!")
  return head_commit == tag_commit

def dependencies_updated(dependencies_built):
  l = map(lambda x: x['updated'], dependencies_built)
  return reduce(lambda a, b: a or b, l, False)

def save_package_info(path, package_info):
  with open(os.path.join(path, 'package.json'), 'w') as outfile:
    json.dump(package_info, outfile, indent=2)
  run_shell_cmd(path, 'git add package.json')
  run_shell_cmd(path, 'git commit -m "v%s"' % package_info['version'])

def merge_and_tag_build(path, version):
  run_shell_cmd(path, 'git checkout --quiet master')
  run_shell_cmd(path, 'git merge --quiet development')
  run_shell_cmd(path, 'git tag -a v%s -m "%s"' % (version, version))
  run_shell_cmd(path, 'git checkout --quiet development')
  run_shell_cmd(path, 'git merge --quiet master')


#########
# setup #
#########

def setup_command(path, chromadir):
  # TODO rm outdated node_modules
  # TODO npm install
  # TODO symlink local chroma packages
  print "not implemented yet ..."


#########
# pull #
#########

def pull_command(path, remote):
  print "not implemented yet ..."


#######
# cli #
#######

def add_validate_command(subparsers):
  validate_parser = subparsers.add_parser(
    'validate', help="validate package and dependencies"
  )
  validate_parser.add_argument("path", help="path to root package")

def add_build_command(subparsers):
  build_parser = subparsers.add_parser(
    'build', help="build package and dependencies"
  )
  build_parser.add_argument("path", help="path to root package")

def add_pull_command(subparsers):
  build_parser = subparsers.add_parser(
    'pull', help="pull package development/master branches and tags"
  )
  build_parser.add_argument("path", help="path to root package")
  build_parser.add_argument(
    "--remote", default="origin",
    help="remote repository (default=origin)"
  )

def add_push_command(subparsers):
  build_parser = subparsers.add_parser(
    'push', help="push package development/master branches and tags"
  )
  build_parser.add_argument("path", help="path to root package")
  build_parser.add_argument(
    "--remote", default="origin",
    help="remote repository (default=origin)"
  )

def add_setup_command(subparsers):
  build_parser = subparsers.add_parser(
    'setup', help="install dependencies and symlink chroma packages"
  )
  build_parser.add_argument("path", help="path to root package")
  build_parser.add_argument(
    "--chromadir", default=os.getcwd(),
    help="location of chroma packages (default=cwd)"
  )

def get_arguments():
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers(title='Commands', dest='command')
  add_setup_command(subparsers)
  add_validate_command(subparsers)
  add_build_command(subparsers)
  add_pull_command(subparsers)
  add_push_command(subparsers)
  return vars(parser.parse_args())

if __name__ == "__main__":
  args = get_arguments()
  commands = {
    "validate" : validate_command,
    "build" : build_command,
    "pull" : pull_command,
    "push" : push_command,
    "setup" : setup_command,
  }
  command = commands[args.pop("command")]
  command(**args)

