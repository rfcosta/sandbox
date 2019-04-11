#!/bin/env python

# This runs from the root crontab.
#
# State can be changed to enabled or disabled with CGI commands.
#    https://{shpUrl}/get_state
#    https://{shpUrl}/set_state?state=enabled
#    https://{shpUrl}/set_state?state=disabled
#
# The state will also change if the health check detects an issue.
#
# If state has been changed, it copies the correct config file and updates the apache conf files
#
# See also: get_state, set_state scripts in the apache reverse proxy ansible role

import os
import requests
from shutil import copyfile

CURRENT_STATE_FILE = '/opt/aed/shp/flags/current_state'
EXPECTED_STATE_FILE = '/opt/aed/shp/flags/expected_state'

APACHE_CONFIG_DIR = '/etc/httpd/conf.d'
APACHE_CONFIG_HEALTHY = APACHE_CONFIG_DIR + '/authentication.healthy.conf'
APACHE_CONFIG_UNHEALTHY = APACHE_CONFIG_DIR + '/authentication.unhealthy.conf'
APACHE_CONFIG_IN_USE = APACHE_CONFIG_DIR + '/authentication.conf'
WAF_URL = "https://servicehealth-dev.sabre.com/grafana".replace('https','http').replace('/grafana', '')

def get_state(fname):
  state = 'enabled'
  try:
    text_file = open(fname, "r")
    state = text_file.read()
    text_file.close()
  except IOError, e:
    print "FATAL: " + str(e)
    state = "enabled"
  return state


def get_current_state():
  return get_state(CURRENT_STATE_FILE)


def get_expected_state():
  return get_state(EXPECTED_STATE_FILE)


def update_apache(conf_file):
  os.chdir("/etc/httpd/conf.d")
  copyfile(conf_file, APACHE_CONFIG_IN_USE)
  os.system("systemctl reload httpd.service")


def save_new_state( state):
  try:
    text_file = open(CURRENT_STATE_FILE, "w")
    text_file.write(state)
    text_file.close()
  except IOError, e:
    print str(e)

  if 'enabled' in state.lower() or 'healthy' in state.lower():
    update_apache(APACHE_CONFIG_HEALTHY)

  if 'disabled' in state.lower() or 'unhealthy' in state.lower():
    update_apache(APACHE_CONFIG_UNHEALTHY)


current_state = get_current_state()
expected_state = get_expected_state()

if current_state != expected_state:
  print "Changing state to " + expected_state
  save_new_state(expected_state)


