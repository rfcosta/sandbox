#!/bin/env python

import urllib
import calendar
import os
import json
from datetime import datetime
from optparse import OptionParser


def encode(service):
    service_name = service.replace(" -", "-")
    service_name = service_name.replace("- ", "-")
    service_name = service_name.replace("_", "-")
    service_name = service_name.replace(" ", "-")
    return service_name


def convert_utc_to_epoch(timestamp_string):
    '''Use this function to convert utc to epoch'''
    print timestamp_string
    try:
        timestamp = datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%S:%fZ')
    except Exception:
        try:
            timestamp = datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%S.%fZ')
        except Exception:
            timestamp = datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%SZ')

    epoch = int(calendar.timegm(timestamp.utctimetuple()))
    print epoch
    return str(epoch) + '000000000'


def LoadJson(json_filename):
    """Load JSON file.
    Raises ValueError if JSON is invalid.

    :filename: path to file containing query
    :returns: dic
    """
    try:
        with open(json_filename) as json_file:
            return json.load(json_file)
    except ValueError as err:
        return dict()



if __name__ == "__main__":

    parser = OptionParser()
    parser.add_option("--csv",       dest="csv"         , default="", help="Input data file",   )
    parser.add_option("--options",   dest="options_file", default="", help="Options json file"  )
    parser.add_option("--service",   dest="service"     , default="", help="Service"            )
    parser.add_option("--key",       dest="key"         , default="", help="Key"                )
    parser.add_option("--metric",    dest="metric"      , default="", help="Metric"             )
    parser.add_option("--source",    dest="source"      , default="", help="Data Source"        )


    (options, args) = parser.parse_args()

    options_file = options.options_file
    OPTIONS = LoadJson(options_file)

    parameterNames = ["csv", "service", "key", "metric", "source"]

    for parm in parameterNames:
        value = options[parm]
        if value:
            OPTIONS[parm] = value

    print "OPTIONS: " + json.dumps(OPTIONS, indent=4)

    # (service, key, metric) = metrics_file.split('^', 3)
    # metric = metric.replace(".csv", "")

    type         = OPTIONS.get("metric")
    metrics_file = OPTIONS.get("csv")
    service      = OPTIONS.get("service")
    key          = OPTIONS.get("key")
    metric       = OPTIONS.get("metric")
    source       = OPTIONS.get("source") # Sources "AppDynamics" | "VIZ" | "Zabbix" | "Service Supplied"

    influx_url = "http://localhost:8086/write?db=kpi"

    first_line = 1

    size = os.stat(metrics_file).st_size
    print "FILE: " + metrics_file + ", Size: " + str(size)

    if (size > 100):
        with open(metrics_file) as f:
            for line in f:
                print line
                if first_line == 1:
                    first_line = 0
                    continue
                line = line.rstrip()

                (when, service, count) = line.split(',', 3)
                print "SERVICE: " + service
                service = encode(service)
                when = str(convert_utc_to_epoch(when))
                print "Type: " + str(type)
                tags = "ci=" + service + ",key=" + key + ",source=" + source + ",type=" + metric
                values = type + "=" + count
                data = "metric," + tags + " " + values + " " + when
                print "DATA: " + data

                command = "curl -s -i -XPOST " + influx_url + " --data-binary \"" + data + "\""
                print command
                os.system(command)

