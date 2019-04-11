#!/bin/env python

import urllib
import calendar
import os
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


parser = OptionParser()
parser.add_option("--metrics_file", dest="metrics_file", default="")
(options, args) = parser.parse_args()

metrics_file = options.metrics_file

print "METRICS FILE: " + metrics_file
(service, key, metric) = metrics_file.split('^', 3)
metric = metric.replace(".csv", "")
type = metric

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
            tags = "ci=" + service + ",key=" + key + ",source=AppDynamics,type=" + metric
            values = type + "=" + count
            data = "metric," + tags + " " + values + " " + when
            print "DATA: " + data

            command = "curl -s -i -XPOST " + influx_url + " --data-binary \"" + data + "\"" 
            print command
            os.system(command)
 
