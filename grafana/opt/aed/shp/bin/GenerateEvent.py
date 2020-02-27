#!/bin/env python

# This python script pulls values from the json sent by Kapacitor and then calls SnowEvent.py to generate an event in ServiceNow

import json
import os
import sys
import copy

sys.path.append('/opt/aed/shp/lib')

import requests
import shputil
import dateutil.parser
import time
from subprocess import call
from select import select
from service_configuration import ServiceConfiguration
from influxdb import InfluxDBClient

MAIN_ORG_ID = 1
STAGING_ORG_ID = 2

# Gets an alert record from Kapacitor and parses out relevant data
def analyzeKapacitorAlert():
    alertData = ""
    # Defaulting fields so we don't have to keep checking in other functions
    singleAlert = {"alertSource": "kapacitor", "level": "", "id": "", "ci": "", "customer_code": ""}

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
        raise KeyError("Unable to find alert message: " + str(kapacitorAlerts))

    if "time" in kapacitorAlerts:
        singleAlert["time"] = str(kapacitorAlerts["time"])
    else:
        raise KeyError("Unable to find time of alert: " + str(kapacitorAlerts))

    if "level" in kapacitorAlerts:
        singleAlert["level"] = str(kapacitorAlerts["level"])
    else:
        raise KeyError("Unable to find alert level: " + str(kapacitorAlerts))

    if "id" in kapacitorAlerts:
        singleAlert["id"] = str(kapacitorAlerts["id"])
    else:
        raise KeyError("Unable to find alert id: " + str(kapacitorAlerts))

    if "data" in kapacitorAlerts and "series" in kapacitorAlerts["data"]:
        if len(kapacitorAlerts["data"]["series"]) > 0:
            if "tags" in kapacitorAlerts["data"]["series"][0]:
                if "ci" in kapacitorAlerts["data"]["series"][0]["tags"]:
                    singleAlert["ci"] = str(kapacitorAlerts["data"]["series"][0]["tags"]["ci"])
                if "type" in kapacitorAlerts["data"]["series"][0]["tags"]:
                    singleAlert["type"] = str(kapacitorAlerts["data"]["series"][0]["tags"]["type"])
                if "key" in kapacitorAlerts["data"]["series"][0]["tags"]:
                    singleAlert["panelKey"] = str(kapacitorAlerts["data"]["series"][0]["tags"]["key"])
                if "customer_code" in kapacitorAlerts["data"]["series"][0]["tags"]:
                    singleAlert["customer_code"] = str(kapacitorAlerts["data"]["series"][0]["tags"]["customer_code"])
            else:
                raise KeyError("Alert data contains no tags: " + str(kapacitorAlerts))
            if "values" in kapacitorAlerts["data"]["series"][0]:
                if "columns" in kapacitorAlerts["data"]["series"][0]:
                    kapacitorColumns = kapacitorAlerts["data"]["series"][0]["columns"]
                    for kapacitorValue in kapacitorAlerts["data"]["series"][0]["values"]:
                        singleAlert["value"] = ""  # reset
                        singleAlert["breached_threshold"] = ""  # reset
                        singleAlert["breach_type"] = ""  # reset
                        lower_threshold = -1
                        upper_threshold = -1
                        if str(singleAlert["type"]) in kapacitorColumns:
                           singleAlert["value"] = kapacitorValue[kapacitorColumns.index(singleAlert["type"])]
                        if singleAlert["message"] == "Dynamic Breach":
                            if "threshold_dynamic_upper" in kapacitorColumns:
                                upper_threshold = kapacitorValue[kapacitorColumns.index("threshold_dynamic_upper")]
                            if "threshold_dynamic_lower" in kapacitorColumns:
                                lower_threshold = kapacitorValue[kapacitorColumns.index("threshold_dynamic_lower")]
                        if str(singleAlert["message"]) == "Static Breach":
                            if "threshold_static_upper" in kapacitorColumns:
                                upper_threshold = kapacitorValue[kapacitorColumns.index("threshold_static_upper")]
                            if "threshold_static_lower" in kapacitorColumns:
                                lower_threshold = kapacitorValue[kapacitorColumns.index("threshold_static_lower")]

                        if upper_threshold < singleAlert["value"]:
                            singleAlert["breach_type"] = "above"
                            singleAlert["breached_threshold"] = upper_threshold
                        if lower_threshold > singleAlert["value"]:
                            singleAlert["breach_type"] = "below"
                            singleAlert["breached_threshold"] = lower_threshold

                        logger.info("Service Alert: " + str(singleAlert))
                        return singleAlert
                else:
                    raise KeyError("Alert data contains no columns: " + str(kapacitorAlerts))
            else:
                raise KeyError("Alert data contains no values: " + str(kapacitorAlerts))
        else:
            raise KeyError("Alert data contains no alerts: " + str(kapacitorAlerts))
    else:
        raise KeyError("Unable to find data in alert: " + str(kapacitorAlerts))


# Creates and sends an event record to ServiceNow
def createServiceNowEvent(kapacitorAlert):
    # Mapping between kapacitor and SNOW alert levels
    # SNOW has several more options than Kapacitor, which only has INFO, WARNING, CRITICAL
    levelMap = ["OK", "CRITICAL", "MAJOR", "MINOR", "WARNING", "INFO"]

    level = 0  # default
    if "level" in kapacitorAlert:
        if kapacitorAlert["level"] in levelMap:
            level = levelMap.index(kapacitorAlert["level"])

    # Do not send CLEAR events for now
    if level == 0:
       logger.debug("Would have sent clear event: " + str(kapacitorAlert))
       return

    service_name = global_ci.replace(" -", "-")
    service_name = service_name.replace("- ", "-")
    service_name = service_name.replace("_", "-")
    service_name = service_name.replace("/", "-")
    service_name = service_name.replace(" ", "-")

    dashboard_uid = global_snowConfigService.dashboard_uid

    servicenow_group_validated = global_config['servicenow_group_validated']
    servicenow_group_staging = global_config['servicenow_group_staging']

    if (global_snowConfigService.is_validated()):
      org_id = MAIN_ORG_ID
      category_key = "true"
    else:
      org_id = STAGING_ORG_ID
      category_key = "false"

    event_class = str(global_config['servicenow_event_class'])

    baseURL = "https://" + str(global_config['service_health_portal_host']) + "/grafana/d/"

    if kapacitorAlert["type"] == "transaction_count":
        alertMessage = "Transaction Count"
    elif kapacitorAlert["type"] == "error_count":
        alertMessage = "Error Count"
    elif kapacitorAlert["type"] == "error_rate":
        alertMessage = "Error Rate"
    elif kapacitorAlert["type"] == "avg_processing_time":
        alertMessage = "Processing Time"
    elif kapacitorAlert["type"] == "count":
        alertMessage = "Count"
    elif kapacitorAlert["type"] == "percent":
        alertMessage = "Percent"
    elif kapacitorAlert["type"] == "currency":
        alertMessage = "Currency"
    else:
        alertMessage = "Other Error"


    graph_title = alertMessage
    if global_panel.title:
        graph_title = global_panel.title


    relation = kapacitorAlert["breach_type"]
    threshold = kapacitorAlert["breached_threshold"]

    message = "Service Health Portal: " + kapacitorAlert["level"] + ": " + global_ci + " " + graph_title + " is " +  str(kapacitorAlert["value"])

    if kapacitorAlert["customer_code"] != "" and kapacitorAlert["customer_code"] != "ALL":
        message = message + " for customer: " + kapacitorAlert["customer_code"]

    if relation != "" and threshold != "":
        if "WARNING" == kapacitorAlert["level"]:
            message = message + " which is " + relation + " the dynamic threshold of " + str(threshold)
        else:
            message = message + " which is " + relation + " the threshold of " + str(threshold)


    d = dateutil.parser.parse(str(kapacitorAlert["time"]))
    snow_alertTime = d.strftime('%Y-%m-%d %H:%M:%S')

    # Show 3 hours before to 1 hour after
    grafanaBeginTime = global_grafanaTime - (180 * 60 * 1000)
    grafanaEndTime = global_grafanaTime + (60 * 60 * 1000)

    kapacitorAlert["u_urgency"] = "1"
    kapacitorAlert["u_category"] = str(category_key)
    kapacitorAlert["u_kb_article"] = str(global_snowConfigService.knowledge_article.split(' ')[0] )
    kapacitorAlert["u_monitoringlink"] = str(baseURL + dashboard_uid + "/" + service_name + '?orgId=' + str(org_id) + '&from=' + str(grafanaBeginTime) + '&to=' + str(grafanaEndTime))
    kapacitorAlert["type"] = str(alertMessage)
    kapacitorAlert["u_short_description"] = str(message)

    snow_script = str(global_config["base_dir"]) + "bin/SnowEvent.py"

    call(["python", snow_script, "--source=Service Health Portal",
          "--eventClass=%s" % event_class,
          "--node=%s" % global_ci, "--timeOfEvent=%s" % snow_alertTime,
          "--type=%s" % alertMessage, "--resource=%s" % global_key, "--severity=%s" % level,
          "--description=%s" % message, "--additionalInfo=%s" % kapacitorAlert])

# Creates a record in the alert measure in influx
def createInfluxAlert(kapacitorAlert):
    influx_measure = str(global_config["influxdb_alert_measure"])

    dash = global_ci.replace(" -", "-")
    dash = dash.replace("- ", "-")
    dash = dash.replace(" ", "-")
    dash = dash.replace("/", "-")

    local_ci = global_ci.replace(" ", "\ ")

    alertType = str(kapacitorAlert["type"])

    level = str(kapacitorAlert["level"])

    overall_service_metric = 'False'
    if global_panel.overall_service_metric:
        if global_panel.overall_service_metric == 'true':
            overall_service_metric = 'True'

    session = requests.Session()
    session.trust_env = False
    resp = requests.post(shputil.get_influxdb_base_url() + "/write?db=" + global_influx_db,
                         influx_measure + ",level=" + level + "," +
                         "ci=" + local_ci + "" + "," +
                         "type=" + alertType + "," +
                         "key=" + global_key + "," +
                         "overall_service_metric=" + overall_service_metric + "," +
                         "validated=" + str(global_snowConfigService.is_validated()) +
                         " dash=\"" + dash + "\"" + " " + str(global_alertTime))
    if resp.status_code != 204:
        raise IOError("Error inserting alert record into InfluxDB: " + str(resp))

# Creates a record in the breach measure in influx
def createInfluxBreach(kapacitorAlert):
    influx_measure = str(global_config["influxdb_breach_measure"])

    dash = global_ci.replace(" -", "-")
    dash = dash.replace("- ", "-")
    dash = dash.replace(" ", "-")

    local_ci = global_ci.replace(" ", "\ ")

    alertType = str(kapacitorAlert["type"])

    level = str(kapacitorAlert["level"])

    overall_service_metric = 'False'
    if global_panel.overall_service_metric:
        if global_panel.overall_service_metric == 'true':
            overall_service_metric = 'True'

    session = requests.Session()
    session.trust_env = False
    resp = requests.post(shputil.get_influxdb_base_url() + "/write?db=" + global_influx_db,
                         influx_measure + ",level=" + level + "," +
                         "ci=" + local_ci + "" + "," +
                         "type=" + alertType + "," +
                         "key=" + global_key + "," +
                         "overall_service_metric=" + overall_service_metric + "," +
                         "validated=" + str(global_snowConfigService.is_validated()) +
                         " dash=\"" + dash + "\"" + " " + str(global_alertTime))
    if resp.status_code != 204:
        raise IOError("Error inserting alert record into InfluxDB: " + str(resp))


# Evaluates if we have had X breaches within the last Y minutes
def x_in_y(kapacitorAlert, levelCheck = 'CRITICAL'):
    influx_measure = str(global_config["influxdb_breach_measure"])
    influx_policy = str(global_config["influxdb_breach_policy"])

    # We need to find out what x and y are for this ci/key combination, but start with defaults (2 consecutive points)
    xTimes = 2
    yMinutes = 2

    if levelCheck == "CRITICAL":
        if global_panel.static_threshold_violation_occurrences:
            xTimes = int(global_panel.static_threshold_violation_occurrences)
        if global_panel.static_threshold_violation_window:
            yMinutes = int(global_panel.static_threshold_violation_window)
    else:
        if global_panel.dynamic_threshold_violation_occurrences:
            xTimes = int(global_panel.dynamic_threshold_violation_occurrences)
        if global_panel.dynamic_threshold_violation_window:
            yMinutes = int(global_panel.dynamic_threshold_violation_window)


    beginTime = global_alertTime - (yMinutes * 60 * 1000000000)
    endTime = global_alertTime + 1000

    query = 'SELECT count(\"dash\") FROM \"' + global_influx_db + '\".\"' + influx_policy + '\".\"' + influx_measure +\
            '\" WHERE time > ' + str(beginTime) + ' AND time <= ' + str(endTime) + ' AND \"ci\"=\'' + global_ci + \
            '\' AND \"key\"=\'' + global_key + '\' AND \"level\"=\'' + levelCheck + '\' AND \"type\"=\'' + str(kapacitorAlert["type"]) + '\''

    #print(query)
    rs = global_db_connection.query(query)
    numberOfBreaches = 0
    #print(str(rs))
    points = rs.get_points()
    for item in points:
        #print(item['count'])
        numberOfBreaches = item['count']
        break

    # If we had too many breaches, return the number of breaches
    if numberOfBreaches >= xTimes:
        return numberOfBreaches
    # If we have not had too many, return -1
    else:
        return -1


def get_db_connection():
    influx_host = global_config['influxdb_host']
    influx_port = global_config['influxdb_port']
    influx_db = global_config['influxdb_db'] + ".\"" + global_config['influxdb_metric_policy'] + "\"." + global_config['influxdb_metric_measure']

    return InfluxDBClient(host=influx_host, port=influx_port, database=influx_db)


os.environ['NO_PROXY'] = shputil.get_influxdb_base_url()

global_config = shputil.get_config()
logger = shputil.get_logger('snow_events')

try:
    global_service_config = ServiceConfiguration()
    global_db_connection = get_db_connection()

    # create an object with data from the alert
    global_singleKapAlert = analyzeKapacitorAlert()

    # Set a bunch of globals from the alert to be used in functions
    global_key = str(global_singleKapAlert["panelKey"])
    global_ci = global_singleKapAlert["ci"]
    global_snowConfigService = global_service_config.get_service(global_ci)
    if global_snowConfigService is None:
        raise KeyError("Service configuration not found for:" + global_ci)

    global_panel = ""
    for panel in global_snowConfigService.panels:
        if panel.panelKey == global_key:
            global_panel = panel
            break

# Do we need to drop seconds from the time (or maybe round) so we only have one breach per minute?
    alert_time = str(global_singleKapAlert["time"])
    try:
        pattern = "%Y-%m-%dT%H:%M:%SZ"
        global_grafanaTime = int(time.mktime(time.strptime(alert_time, pattern))) * 1000
    except ValueError as ve:
        pattern = "%Y-%m-%dT%H:%M:%S.%fZ"
        global_grafanaTime = int(time.mktime(time.strptime(alert_time, pattern))) * 1000
    global_alertTime = global_grafanaTime * 1000000

    global_influx_db = str(global_config["influxdb_db"])


    # Create a record in the influxdb breach measure
    createInfluxBreach(copy.copy(global_singleKapAlert))

    # Find the number of breaches in the last window
    numberOfBreaches = x_in_y(copy.copy(global_singleKapAlert), str(global_singleKapAlert["level"]))
    # If we've had too many breaches, create influx alert and ServiceNow event
    if numberOfBreaches > 0:
        createInfluxAlert(copy.copy(global_singleKapAlert))
        # If this is a WARNING, that means it was from a dynamic threshold.  If so, we need to first see if the static
        # threshold check did/will create an event - we don't want both.
        if 'CRITICAL' == str(global_singleKapAlert["level"]) or (0 > x_in_y(copy.copy(global_singleKapAlert), 'CRITICAL')):
            createServiceNowEvent(copy.copy(global_singleKapAlert))

except Exception as e:
    logger.exception(e)
