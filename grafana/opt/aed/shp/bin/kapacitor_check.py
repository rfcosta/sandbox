import sys
import json
import os
import re
import datetime
import dateutil.parser

sys.path.append('/opt/aed/shp/lib')

import logging
import logging.config
import shputil
from subprocess import call
from service_configuration import ServiceConfiguration

# Adds
def processReceivedList(workingIncompleteGroups, localReceivedList, metricsPrefix, thresholdsPrefix, joinedPrefix):

    for service in localReceivedList:
        ciConfig = service_config.get_service(service)
        # We only want to report on validated services
        # Do we also want 'Staging - Alerting'? - if so, change to is_alerting()
        if ciConfig.is_validated():
            for key in localReceivedList[service]:
                tickName = "unknown"
                alertingEnabled = False
                for panel in ciConfig.panels:
                    if panel.panelKey == key:
                        tickName = "kpi_" + str(panel.metric_type)
                        if panel.alerting_enabled == "true":
                            alertingEnabled = True

                # We only want to report on panels that have alerting enabled
                if alertingEnabled:
                    # print "key is " + key
                    foundCompleteSet = False
                    foundProcessed = False
                    missingProcessed = False
                    for dataTime in localReceivedList[service][key]:
                        # Grab the TICK name from whatever we have
                        if metricsPrefix in localReceivedList[service][key][dataTime]:
                            tickName = localReceivedList[service][key][dataTime][metricsPrefix]
                        elif thresholdsPrefix in localReceivedList[service][key][dataTime]:
                            tickName = localReceivedList[service][key][dataTime][thresholdsPrefix]
                        elif joinedPrefix in localReceivedList[service][key][dataTime]:
                            tickName = localReceivedList[service][key][dataTime][joinedPrefix]

                        if metricsPrefix in localReceivedList[service][key][dataTime] and thresholdsPrefix in localReceivedList[service][key][dataTime] and joinedPrefix in localReceivedList[service][key][dataTime]:
                            foundCompleteSet = True
                            foundProcessed = True
                        # If we have metrics and thresholds, we should have processed.  If we don't also have a join, mark it.
                        if metricsPrefix in localReceivedList[service][key][dataTime] and thresholdsPrefix in localReceivedList[service][key][dataTime] and joinedPrefix not in localReceivedList[service][key][dataTime]:
                            missingProcessed = True
                        # If we have joinedPrefix, and either metrics or thresholds, then count processed
                        # We don't want to count if we only have joinedPrefix, because that could be processing old data
                        if joinedPrefix in localReceivedList[service][key][dataTime]:
                            if metricsPrefix in localReceivedList[service][key][dataTime] or thresholdsPrefix in localReceivedList[service][key][dataTime]:
                                foundProcessed = True
                            else:
                                # What do we do with this???
                                processedOldData = True

                    if not foundCompleteSet:
                        # print("No set found for " + str(ciConfig.name) + " " + tickName)
                        # print(localReceivedList[service][key])
                        if service not in workingIncompleteGroups["notComplete"]:
                            workingIncompleteGroups["notComplete"][service] = []

                        if tickName not in workingIncompleteGroups["notComplete"][service]:
                            workingIncompleteGroups["notComplete"][service].append(tickName)

                    # If we didn't find any joins, but we had at least one minute with both metric and threshold
                    if missingProcessed and not foundProcessed:
                        if service not in workingIncompleteGroups["notProcessed"]:
                            workingIncompleteGroups["notProcessed"][service] = []

                        if tickName not in workingIncompleteGroups["notProcessed"][service]:
                            workingIncompleteGroups["notProcessed"][service].append(tickName)

                        # Not sure if we want to add this - could be too much data
                        #if service not in addDetails["failureSets"]":
                        #    addDetails["failureSets"][service] = {}
                        #if key not in addDetails["failureSets"][service]:
                        #    addDetails["failureSets"][service][key] = []
                        #addDetails["failureSets"][service][key].append(localReceivedList[service][key])

    return workingIncompleteGroups


service_config = ServiceConfiguration()
logging.config.fileConfig("/opt/aed/shp/conf/kapacitor_check.ini")
services = service_config.get_services()

config = shputil.get_config()
service_config = ServiceConfiguration()

# Number of minutes before the end of the file to begin collecting information
startLooking = 15
# Number of minutes before the end of the file to stop collecting information (we expect some to be incomplete)
stopLooking = 3

logging.info("Running kapacitor_check")
logging.info("")

# Find the last line in kapacitor.log, and use that to set the start/end timestamps
with open('/var/log/kapacitor/kapacitor.log', 'rb') as f:
    f.seek(-2, os.SEEK_END)
    while f.read(1) != b'\n':
        f.seek(-2, os.SEEK_CUR)
    lastLine = f.readline().decode('utf-8')
    lineDict = dict(re.findall(r'(\S+)=(".*?"|\S+)', lastLine))
    lastTS = dateutil.parser.parse(lineDict['ts'])
    lookBack = lastTS - datetime.timedelta(minutes=startLooking)
    tooRecent = lastTS - datetime.timedelta(minutes=stopLooking)
    # print(lineDict['ts'])
    lookBackTime = "ts=" + lookBack.strftime('%Y-%m-%dT%H:%M')
    tooRecentTime = "ts=" + tooRecent.strftime('%Y-%m-%dT%H:%M')
    # print(lookBackTime)

receivedList = {}

with open('/var/log/kapacitor/kapacitor.log') as kapLog:
    # Skip likes before lookBackTime
    for line in kapLog:
        if -1 != line.find(lookBackTime, 0, 20):
            break

    for line in kapLog:
        # If we have reached tooRecentTime, we can stop collecting
        if -1 != line.find(tooRecentTime, 0, 20):
            break
        # Collect data
        if -1 != line.find("msg=point"):
            try:
                msgDict = dict(re.findall(r'(\S+)=(".*?"|\S+)', line))
                if 'tag_ci' in msgDict:
                    ci = re.sub('["]', '', msgDict['tag_ci'])
                else:
                    logging.warning("Missing ci on line: " + line)
                    continue
                if 'tag_key' in msgDict:
                    key = msgDict['tag_key']
                else:
                    logging.warning("Missing key on line: " + line)
                    continue
                if 'tag_type' in msgDict:
                    type = msgDict['tag_type']
                else:
                    type = "none"
                if 'task' in msgDict:
                    tickTask = msgDict['task']
                else:
                    tickTask = "unknown"
                if 'prefix' in msgDict:
                    prefix = msgDict['prefix']
                else:
                    logging.warning("Missing prefix on line: " + line)
                    continue
                dataTime = msgDict['time'][:16]
                if ci not in receivedList:
                    receivedList[ci] = {}
                if key not in receivedList[ci]:
                    receivedList[ci][key] = {}
                if dataTime not in receivedList[ci][key]:
                    receivedList[ci][key][dataTime] = {}
                if prefix not in receivedList[ci][key][dataTime]:
                    receivedList[ci][key][dataTime][prefix] = {}
                # Put the TICK task in each attribute, so we can pull from whatever we have
                receivedList[ci][key][dataTime][prefix] = tickTask

            except Exception as e:
                logging.exception("Caught Error:  " + str(e))

addDetails = {}
addDetails["u_assignment_group"] = "Service Health Portal"
addDetails["u_urgency"] = "1"
#addDetails["u_kb_article"] = str(snowConfigService.knowledge_article.split(' ')[0] )
#addDetails["u_monitoringlink"] = str(baseURL + dashboard_uid + "/" + service_name + '?orgId=' + str(org_id))
addDetails["failureSets"] = {}

# Initialize the incompleteGroups object
incompleteGroups = {"notComplete": {}, "notProcessed": {}}

#print(receivedList)
incompleteGroups = processReceivedList(incompleteGroups, receivedList, 'metrics', 'thresholds', 'joined')
incompleteGroups = processReceivedList(incompleteGroups, receivedList, 'dynamic_data', 'dynamic_trend', 'dynamic_join')
#print(incompleteGroups)

# for missingService in incompleteGroups["notComplete"]:
#    logging.warning("Service " + missingService + " is missing completed groups for " + str(incompleteGroups["notComplete"][missingService]))

stuckScripts = []
for missingService in incompleteGroups["notProcessed"]:
    logging.warning("Service " + missingService + " is missing join for " + str(incompleteGroups["notProcessed"][missingService]))
    addDetails["failureSets"][missingService] = str(incompleteGroups["notProcessed"][missingService])

    # Not sure we want to auto-cycle the TICK scripts, but playing around just in case
    # Build list of scripts to cycle
    for scriptName in incompleteGroups["notProcessed"][missingService]:
        if scriptName not in stuckScripts:
            stuckScripts.append(scriptName)

# Not sure we want to auto-cycle the TICK scripts, but playing around just in case
scriptCount = 0
snow_script = str(config["base_dir"]) + "bin/SnowEvent.py"
event_class = str(config['servicenow_event_class'])
message = "These TICK scripts are not processing for at least one service: "
for script in stuckScripts:
    #print "Should be Cycling stuck TICK script -" + script + "-"
    if scriptCount > 0:
        message = message + ", "
    message = message + str(script)
    scriptCount += 1

    # logging.info("Should be Cycling stuck TICK script -" + script + "-")
    logging.info("Cycling stuck TICK script -" + script + "-")
    os.system("/usr/bin/kapacitor " + "disable " + script)
    os.system("/usr/bin/kapacitor " + "enable " + script)

addDetails["u_short_description"] = message

## ANDREW - Need to watch for TICKs getting disabled and not re-enabled.  Maybe a check at the end?

# If we had any problems, send an event to ServiceNow
if scriptCount > 0:
    call(["python", snow_script, "--source=Service Health Portal",
      "--eventClass=%s" % event_class,
      "--node=Service Health Portal", "--severity=1",
      "--type=Kapacitor Check", "--resource=",
      "--description=%s" % message, "--additionalInfo=%s" % str(addDetails)])
# Otherwise send OK -- maybe not yet
#else:
#    message = "Did not find any stuck TICK scripts"
#    addDetails["u_short_description"] = message
#    call(["python", snow_script, "--source=Service Health Portal",
#      "--eventClass=%s" % event_class,
#      "--node=Service Health Portal", "--severity=0",
#      "--type=Kapacitor Check", "--resource=",
#      "--description=%s" % message, "--additionalInfo=%s" % str(addDetails)])


logging.info("Finished kapacitor_check")
logging.info("")
