#!/bin/env python

# This python script sends an Event to the ServiceNow instance Event Management system via REST.
# Sample usage:
#   python sendEventServiceNow.py --source="Source1" --node="lnux100" --type="High Memory Utilization" --resource="RAM" --severity="1"

import base64
import datetime
import json
from optparse import OptionParser
import urllib2
import logging

import sys
sys.path.append('/opt/aed/shp/lib')

import shputil

config = shputil.get_config()
shputil.configure_logging(config["logging_configuration_file"])

snow_user = str(config["servicenow_user"])
snow_pass = str(config["servicenow_pass"])
snow_endpoint = "https://" + str(config["servicenow_instance"]) + ".service-now.com/api/now/table/em_event"

proxy_handler = urllib2.ProxyHandler({
              "http"  : str(config["http_proxy"]),
              "https" : str(config["https_proxy"]),
            })

opener = urllib2.build_opener(proxy_handler)
# ...and install it globally so it can be used with urlopen.
urllib2.install_opener(opener)

def defineOptions():
    parser = OptionParser()

    # How to connect/login to the ServiceNow instance
    parser.add_option("--endPoint", dest="endPoint", help="The endpoint of the web service", default=snow_endpoint)
    parser.add_option("--user", dest="user", help="The user name credential", default=snow_user)
    parser.add_option("--password", dest="password", help="The user password credential", default=snow_pass)

    # Fields on the Event
    parser.add_option("--source", dest="source", help="Source of the event", default="Icinga")
    parser.add_option("--eventClass", dest="eventClass", help="Event class", default="Icinga")
    parser.add_option("--messageKey", dest="messageKey", help="Message key", default="")
    parser.add_option("--node", dest="node", help="Name of the node", default="Default-Node")
    parser.add_option("--type", dest="type", help="Type of event", default="High Memory Utilization")
    parser.add_option("--resource", dest="resource", help="Represents the resource event is associated with", default="Default-Disk")
    parser.add_option("--severity", dest="severity", help="Severity of event", default="3")
    parser.add_option("--timeOfEvent", dest="timeOfEvent", help="Time of event in GMT format", default="")
    parser.add_option("--description", dest="description", help="Event description", default="Default event description")
    parser.add_option("--additionalInfo", dest="additionalInfo", help="Additional event information that can be used for third-party integration or other post-alert processing", default="{}")
    parser.add_option("--ciIdentifier", dest="ciIdentifier", help="Optional JSON string that represents a configuration item", default="{}")

    (options, args) = parser.parse_args()
    return options

def execute():
    if (options.timeOfEvent == ""):
      options.timeOfEvent = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    if options.eventClass == "":
        options.eventClass = options.source

    if options.messageKey == "":
        options.messageKey = options.source +"__" + options.node +"__" + options.type + "__" + options.resource

    data = {"source" : options.source, "node" : options.node , "type" : options.type,
            "resource" : options.resource, "severity" : options.severity,
            "time_of_event" : options.timeOfEvent, "description" : options.description,
            "additional_info" : options.additionalInfo, "ci_identifier" : options.ciIdentifier,
            "event_class" : options.eventClass, "message_key": options.messageKey}
    data = json.dumps(data)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
    request = urllib2.Request(url=options.endPoint, data=data, headers=headers)
    base64string = base64.urlsafe_b64encode('%s:%s' % (options.user, options.password))
    request.add_header("Authorization", "Basic %s" % base64string)
    f = urllib2.urlopen(request)
    f.read()
    f.close()

try:
  options = defineOptions()
  execute()
except Exception, e:
  logging.error("Failure: Unable to create ServiceNow event", exc_info=True)
