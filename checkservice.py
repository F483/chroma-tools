#!/usr/bin/env python

import argparse, sys, urllib2, json

def check_cwpp():
  # cwpp.chromapass.net
  sys.exit("TODO check if cwpp is online!")

def check_p2ptrade():
  try:
    url = "http://p2ptrade.btx.udoidio.info/messages" # get from arguments ?
    json.loads(urllib2.urlopen(url).read())
    print "p2ptrade online!"
  except:
    sys.exit("p2ptrade is offline!")

def check_faucet():
  sys.exit("TODO check if faucet is online!")

def add_check_cwpp(subparsers):
  build_parser = subparsers.add_parser(
    'cwpp', help="Check if cwpp service is online."
  )

def add_check_p2ptrade(subparsers):
  build_parser = subparsers.add_parser(
    'p2ptrade', help="Check if p2ptrade service is online."
  )

def add_check_faucet(subparsers):
  build_parser = subparsers.add_parser(
    'faucet', help="Check if faucet service is online."
  )

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

