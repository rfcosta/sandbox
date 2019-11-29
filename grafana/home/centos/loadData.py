#!/bin/env python3

import urllib
import calendar
import os
import json
import sys
from datetime import datetime
from optparse import OptionParser
import csv
import copy
import re

def encode(service):
    service_name = service.replace(" -", "-")
    service_name = service_name.replace("- ", "-")
    service_name = service_name.replace("_", "-")
    service_name = service_name.replace(" ", "-")
    return service_name

def encode2(service):
    service_name = service.replace(" ", "\\ ")
    return service_name



def convert_utc_to_epoch(timestamp_string):
    '''Use this function to convert utc to epoch'''
    print (timestamp_string)
    try:
        timestamp = datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%S:%fZ')
    except Exception as E1:
        try:
            timestamp = datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%S.%fZ')
        except Exception as E2:
            try:
                timestamp = datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%SZ')
            except Exception as E3:
                timestamp = datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%S %z')

    epoch = int(calendar.timegm(timestamp.utctimetuple()))
    print (epoch)
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

    parser = OptionParser(add_help_option=False)
    parser.add_option("-h",   "--help",      action="help")
    parser.add_option("-f",   "--file",      dest="csv"         , help="Input data file"  , default='')
    parser.add_option("-t",   "--csvtype",   dest="csvtype"     , help="Input data format", default='export')
    parser.add_option("-o",   "--options",   dest="options_file", help="Options json file", default='')
    parser.add_option("-v",   "--service",   dest="service"     , help="Service"          , default='')
    parser.add_option("-k",   "--key",       dest="key"         , help="Key"              , default='')
    parser.add_option("-m",   "--metric",    dest="metric"      , help="Metric"           , default='')
    parser.add_option("-s",   "--source",    dest="source",
                         help='Data Source (AppDynamics | VIZ | Zabbix | Service Supplied)',
                         type="choice", choices=["AppDynamics", "VIZ", "Zabbix", "Service Supplied", ""], default=''
                     )
    parser.add_option("-u",   "--url",       dest="url"         , help="Influx URL"       , default='http://localhost:8086/write?db=kpi')


    (options, args) = parser.parse_args()

    # ----------------------------------------------------------------------------------------------------------
    # The following statement is just to ilustrate how to address the attributes of an object like a dictionary
    #       options.__dict__['source'] = 'VIZ' if not options.source else options.source
    # ----------------------------------------------------------------------------------------------------------

    options_from_json = dict()
    if options.options_file:
        options_from_json = LoadJson(options.options_file)

    # The following onlyt works on Python 2:
    # options_from_json.update(  (ky, val) for (ky,val) in options.__dict__.iteritems() if val  )

    options_from_json.update(  (ky, val) for (ky,val) in options.__dict__.items() if val  )


    #update back options after the overides
    options.__dict__.update(options_from_json)

    print("Options: " + str(options))

    if not options.service or not options.metric or not options.source or not options.key or not options.csv:
        print("**ERROR** All options service, metric, source, key, csv must be specified from command options + options_file (-o or --options_file)")
        exit(8)


    influx_url = options.url # "http://localhost:8086/write?db=kpi"

    first_line = 1
    column_names = []
    rowObject = {}

    _sources = {"AppDynamics": "AppDynamics", "Service Supplied": "ServiceSupplied", "Prometheus": "Prometheus"}
    _service = encode2(options.service)
    # _service = '"{}"'.format(options.service)
    _type = str(options.metric)
    _source = _sources[options.source] if options.source in _sources else _sources['Service Supplied']
    _key = str(options.key)

    size = os.stat(options.csv).st_size
    print ("FILE: " + options.csv + ", Size: " + str(size))

    if (size > 100 and options.csvtype == 'export'):
        with open(options.csv, 'rt')as f:
            data = csv.reader(f, delimiter=';', doublequote=0, lineterminator='\n')

            for row in data:
                if first_line == 1:
                    for col in row:
                        # on first record the 1st column header starts with a couple of invidible chars
                        doublequoteisat = col.find('"')
                        if doublequoteisat > 0:
                            cname = col[doublequoteisat+1: -1]
                        else:
                            cname = str(col)

                        column_names.append(cname)
                        rowObject[cname] = ""
                    first_line = 0
                    continue
                pass

                thisRow = copy.copy(rowObject)
                for (cindex, cvalue) in enumerate(row):
                    if cvalue == 'null':
                        cvalue = ''
                    thisRow[column_names[cindex]] = cvalue

                print(json.dumps(thisRow, indent=4))

                _count = thisRow[options.metrictitle]
                if not _count.isdigit():
                    continue

                when = str(convert_utc_to_epoch(thisRow["Time"]))
                tags = "ci=" + _service + ",key=" + _key + ",source=" + _source + ",type=" + _type
                values = _type + "=" + _count
                data = "metric," + tags + " " + values + " " + when

                print ("SERVICE: {}, Type: {}, DATA: {}".format(_service, _type, data))

                command = "curl -s -i -XPOST " + influx_url + " --data-binary \"" + data + "\""
                print (command)
                os.system(command)
                pass
            pass
        pass
    pass

    if (size > 100 and options.csvtype != 'export'):
        with open(options.csv) as f:
            for line in f:
                print (line)
                if first_line == 1:
                    first_line = 0
                    continue
                line = line.rstrip()

                (when, service, count) = line.split(',', 3)
                when = str(convert_utc_to_epoch(when))
                tags = "ci=" + _service + ",key=" + _key + ",source=" + _source + ",type=" + _type
                values = options.metric + "=" + count
                data = "metric," + tags + " " + values + " " + when

                print ("SERVICE: " + service          )
                print ("Type: " + str(options.metric) )
                print ("DATA: " + data                )

                command = "curl -s -i -XPOST " + influx_url + " --data-binary \"" + data + "\""
                print (command)
                os.system(command)
            pass
        pass
    pass


    # ----------------------------------------------------------------------------------------------------------
    # OLD CODE memory
    # The following code used to use filename with service, key and metric within the file name
    # Deprecated by the new program options and json options file
    # ----------------------------------------------------------------------------------------------------------
    #       (service, key, metric) = metrics_file.split('^', 3)
    #       metric = metric.replace(".csv", "")
    # ----------------------------------------------------------------------------------------------------------



