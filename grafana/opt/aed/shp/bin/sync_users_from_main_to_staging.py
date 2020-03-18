#!/bin/env python3

# This script creates staging and aggregate users for all users in the main org that don't already exist in staging

import requests
import json
from requests.auth import HTTPBasicAuth

import sys

sys.path.append('/opt/aed/shp/lib')

import shputil

shputil.check_logged_in_user('centos')

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
    requests.post(base_url + "/api/orgs/" + str(org_id) + "/users", data=json.dumps(data), headers=headers, auth=credentials)
    logger.debug("Added user: " + user_name + " to secondary org: " + str(org_id))


try:

    headers = {"Accept": "application/json", "Content-type": "application/json"}

    config = shputil.get_config()
    logger = shputil.get_logger("shp")
    user = config['grafana_user']
    password = config['grafana_pass']
    base_url = "http://" + config['grafana_host']

    credentials = HTTPBasicAuth(user, password)

    main_users = get_all_users_in_org(headers, credentials, MAIN_ORG_ID)
    staging_users = get_all_users_in_org(headers, credentials, STAGING_ORG_ID)
    aggregate_users = get_all_users_in_org(headers, credentials, AGGREGATE_ORG_ID)

    for user in main_users:
        if user not in staging_users:
            create_org_user(user, STAGING_ORG_ID, base_url, headers, credentials)
        if user not in aggregate_users:
            create_org_user(user, AGGREGATE_ORG_ID, base_url, headers, credentials)
except Exception as e:
    logger.exception("Failure: Error syncing users to staging or aggregate")
