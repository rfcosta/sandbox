#!/bin/env python3

# This script creates a cloudwatch log_group if it doesn't exist.
# It also sets the correct retention days

import os
import boto3
import json

CONFIG_FILE = "/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.d/shp.json"


def log_group_exists(client, log_group):
    log_groups = client.describe_log_groups(
        logGroupNamePrefix=log_group
    )

    found_log_group = False

    for next_log_group in log_groups["logGroups"]:
        if next_log_group['logGroupName'] == log_group:
            found_log_group = True
            break

    return found_log_group


def create_log_group(client, log_group):
    print("Creating log group: " + log_group)

    response = client.create_log_group(
        logGroupName=log_group,
    )

    meta_data = response['ResponseMetadata']
    if meta_data['HTTPStatusCode'] != 200:
        raise Exception("Failed to create log_group: " + log_group)


def set_retention_period(client, log_group, retention_in_days):
    print("Setting retention period for log group: " + log_group + " to " + retention_in_days + " days")
    response = client.put_retention_policy(
        logGroupName=log_group,
        retentionInDays=int(retention_in_days))

    meta_data = response['ResponseMetadata']
    if meta_data['HTTPStatusCode'] != 200:
        raise Exception("Failed to set retention policy for log_group: " + log_group)


def configure_log_group(client, log_group, retention_in_days):
    if log_group_exists(client, log_group) is False:
        create_log_group(client, log_group)

    set_retention_period(client, log_group, retention_in_days)


def get_log_groups():
    log_groups = []
    file = open(CONFIG_FILE, mode='r')
    config = file.read()
    file.close()

    c = json.loads(config)
    for log in c['logs']['logs_collected']['files']['collect_list']:
        log_group_name = log['log_group_name']
        log_groups.append(log_group_name)

    return log_groups


# mainline

log_groups = get_log_groups()

region = os.environ['AWS_REGION']
retention_in_days = "30"

client = boto3.client('logs', region_name=region)

for log_group in log_groups:
    print("group=" + log_group + " retention=" + retention_in_days)
    configure_log_group(client, log_group, retention_in_days)
