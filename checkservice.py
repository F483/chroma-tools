#!/usr/bin/env python

import argparse, sys, urllib2, json, httplib
from urlparse import urlparse

def get_status(url):
  parse_result = urlparse(url)
  conn = httplib.HTTPConnection(parse_result.hostname)
  conn.request("HEAD", parse_result.path)
  return conn.getresponse().status

def check_cwpp(url):
  try:
    status = get_status(url)
    if status == 502:
      raise Exception()
    print "cwpp service online!"
  except:
    sys.exit("Error: faucet service offline!")

def check_p2ptrade(url):
  try:
    json.loads(urllib2.urlopen(url).read())
    print "p2ptrade service online!"
  except:
    sys.exit("Error: p2ptrade service offline!")

def check_faucet(url):
  try:
    status = get_status(url)
    if status != 200:
      raise Exception(status)
    print "faucet service online!"
  except:
    sys.exit("Error: faucet service offline!")

def add_check_cwpp(subparsers):
  build_parser = subparsers.add_parser(
    'cwpp', help="Check if cwpp service is online."
  )
  url = "http://cwpp.chromapass.net/"
  build_parser.add_argument("--url", default=url, help="Default: %s" % url)

def add_check_p2ptrade(subparsers):
  build_parser = subparsers.add_parser(
    'p2ptrade', help="Check if p2ptrade service is online."
  )
  url = "http://p2ptrade.btx.udoidio.info/messages"
  build_parser.add_argument("--url", default=url, help="Default: %s" % url)

def add_check_faucet(subparsers):
  build_parser = subparsers.add_parser(
    'faucet', help="Check if faucet service is online."
  )
  url = "http://chromaway.com/faucet/"
  build_parser.add_argument("--url", default=url, help="Default: %s" % url)

def get_arguments():
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers(title='Commands', dest='command')
  add_check_faucet(subparsers)
  add_check_p2ptrade(subparsers)
  add_check_cwpp(subparsers)
  return vars(parser.parse_args())

if __name__ == "__main__":
  args = get_arguments()
  commands = {
    "faucet" : check_faucet,
    "p2ptrade" : check_p2ptrade,
    "cwpp" : check_cwpp,
  }
  command = commands[args.pop("command")]
  command(**args)

