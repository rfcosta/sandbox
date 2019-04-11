#!/bin/env python

# This python script pulls values from the json sent by Kapacitor and then calls SnowEvent.py to generate an event in ServiceNow

import json
import os
import sys

sys.path.append('/opt/aed/shp/lib')

import requests
import shputil
import collections
import dateutil.parser
import time
import logging
from time import strftime
from subprocess import call
from select import select
from service_configuration import ServiceConfiguration

sys.path.append('/opt/aed/shp/lib')
import shputil

MAIN_ORG_ID = 1
STAGING_ORG_ID = 2

def processDeadmanAlert():
    alertData = ""
    # Defaulting fields so we don't have to keep checking in other functions
    singleAlert = {"alertSource": "kapacitor", "level": "", "id": "", "ci": "Service Health Portal", "panelKey": ""}
    kapacitorColumns = []

    # We don't want to block
    timeout = 0
    # See if we have any input
    rlist, _, _ = select([sys.stdin], [], [], timeout)
    if rlist:
        alertData = sys.stdin.read()
    else:
        raise IOError("Missing alert data from stdin")

    kapacitorAlerts = json.loads(alertData)

    if "message" in kapacitorAlerts:
        singleAlert["message"] = str(kapacitorAlerts["message"])
    else:
        raise KeyError("Unable to find alert message: " + str(kapacitorAlert))

    if "time" in kapacitorAlerts:
        singleAlert["time"] = str(kapacitorAlerts["time"])
    else:
        raise KeyError("Unable to find time of alert: " + str(kapacitorAlert))

    if "level" in kapacitorAlerts:
        singleAlert["level"] = str(kapacitorAlerts["level"])
    else:
        raise KeyError("Unable to find alert level: " + str(kapacitorAlert))

    if "id" in kapacitorAlerts:
        singleAlert["id"] = str(kapacitorAlerts["id"])
    else:
        raise KeyError("Unable to find alert id: " + str(kapacitorAlert))

    if "data" in kapacitorAlerts and "series" in kapacitorAlerts["data"]:
        if len(kapacitorAlerts["data"]["series"]) > 0:
            if "tags" in kapacitorAlerts["data"]["series"][0]:
                if "ci" in kapacitorAlerts["data"]["series"][0]["tags"]:
                    singleAlert["ci"] = str(kapacitorAlerts["data"]["series"][0]["tags"]["ci"])
                if "key" in kapacitorAlerts["data"]["series"][0]["tags"]:
                    singleAlert["panelKey"] = str(kapacitorAlerts["data"]["series"][0]["tags"]["key"])

    logging.debug("SingleAlert: " + str(singleAlert))
    createServiceNowDeadmanEvent(singleAlert)


def createServiceNowDeadmanEvent(kapacitorAlert):
    # Mapping between kapacitor and SNOW alert levels
    # SNOW has several more options than Kapacitor, which only has INFO, WARNING, CRITICAL
    levelMap = ["OK", "CRITICAL", "MAJOR", "MINOR", "WARNING", "INFO"]

    level = 0  # default
    if "level" in kapacitorAlert:
        if kapacitorAlert["level"] in levelMap:
            level = levelMap.index(kapacitorAlert["level"])

    ci = str(kapacitorAlert["ci"])

    snowConfigService = service_config.get_service(ci)
    if snowConfigService is None:
        raise KeyError("Service configuration not found for:" + ci)

    servicenow_group_validated = config['servicenow_group_validated']
    servicenow_group_staging = config['servicenow_group_staging']

    panelKey = str(kapacitorAlert["panelKey"])

    if (snowConfigService.is_alerting()):
        # For now, we want assigned to staging
        assignment_group = str(servicenow_group_staging)
    else:
        logging.debug("Service is not set to alerting")
        return


    #if (snowConfigService.is_validated()):
    #  org_id = MAIN_ORG_ID
    #  assignment_group = str(servicenow_group_validated)
    #else:
    #  org_id = STAGING_ORG_ID
    #  assignment_group = str(servicenow_group_staging)

    event_class = str(config['servicenow_event_class'])

    #baseURL = "https://" + str(config['service_health_portal_host']) + "/grafana/d/"

    if kapacitorAlert["level"] == "OK":
        message = "Service Health Portal: " + kapacitorAlert["level"] + ": " + "Again receiving " + panelKey + " metrics for " + ci
    else:
        message = "Service Health Portal: " + kapacitorAlert["level"] + ": " + "Not receiving " + panelKey + " metrics for " + ci

    alertMessage = str(kapacitorAlert["message"])

    d = dateutil.parser.parse(str(kapacitorAlert["time"]))
    alertTime = d.strftime('%Y-%m-%d %H:%M:%S')

    kapacitorAlert["u_urgency"] = "1"
    kapacitorAlert["u_assignment_group"] = assignment_group
    kapacitorAlert["u_kb_article"] = str(snowConfigService.knowledge_article.split(' ')[0] )
    #kapacitorAlert["u_monitoringlink"] = str(baseURL + dashboard_uid + "/" + service_name + '?orgId=' + str(org_id))
    kapacitorAlert["type"] = alertMessage
    kapacitorAlert["u_short_description"] = message

    snow_script = str(config["base_dir"]) + "bin/SnowEvent.py"

    call(["python", snow_script, "--source=Service Health Portal",
          "--eventClass=%s" % event_class,
          "--node=%s" % ci, "--timeOfEvent=%s" % alertTime,
          "--type=%s" % alertMessage, "--resource=%s" % panelKey, "--severity=%s" % level,
          "--description=%s" % message, "--additionalInfo=%s" % kapacitorAlert])


try:
    config = shputil.get_config()
    shputil.configure_logging(config["logging_configuration_file"])
    service_config = ServiceConfiguration()

    processDeadmanAlert()
except Exception, e:
    logging.error("Failure: Unable to process event", exc_info=True)
