#!/bin/env python

# This script creates staging and aggregate users for all users in the main org that don't already exist in staging

import requests
import json
from requests.auth import HTTPBasicAuth
import logging

import sys
sys.path.append('/opt/aed/shp/lib')

import shputil

MAIN_ORG_ID = 1
STAGING_ORG_ID = 2
AGGREGATE_ORG_ID = 3

def get_all_users_in_org(headers, credentials, org_id):
  users_found = dict()
  resp = requests.get(base_url + "/api/orgs/" + str(org_id) + "/users", headers=headers, auth=credentials)
  users = json.loads(resp.text)
  for user in users:
      users_found[user['login']] = user
  return users_found

def create_org_user(user_name, org_id, base_url, headers, credentials):
   data = {"loginOrEmail": user_name, "role": "Viewer"}
   resp = requests.post(base_url + "/api/orgs/" + str(org_id) + "/users", data = json.dumps(data), headers=headers, auth=credentials)
   logging.debug("Added user: " + user_name + " to secondary org: " + str(org_id))

try:

  headers = {"Accept":"application/json", "Content-type": "application/json"}

  config = shputil.get_config()
  shputil.configure_logging(config["logging_configuration_file"])
  user=config['grafana_user']
  password=config['grafana_pass']
  base_url="http://" + config['grafana_host']

  credentials = HTTPBasicAuth(user,password)

  main_users =  get_all_users_in_org(headers, credentials, MAIN_ORG_ID)
  staging_users =  get_all_users_in_org(headers, credentials, STAGING_ORG_ID)
  aggregate_users =  get_all_users_in_org(headers, credentials, AGGREGATE_ORG_ID)

  for user in main_users:
    if user not in staging_users:
      create_org_user(user, STAGING_ORG_ID, base_url, headers, credentials)
    if user not in aggregate_users:
      create_org_user(user, AGGREGATE_ORG_ID, base_url, headers, credentials)
except Exception, e:
    logging.error("Failure: Error syncing users to staging or aggregate", exc_info=True)