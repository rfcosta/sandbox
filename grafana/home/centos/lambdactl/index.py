#!/bin/env python3

import sys
import os
import json
# import time

# sys.path.append('.')

from influx_util import InfluxUtil
from aws_util import AwsUtil
from aws_vars import AwsVars


PYTHON = sys.version
AWS = AwsUtil(__name__)
loggger = AWS.loggger
AWSVARS = AwsVars(AWS)

BASE_PATH = os.path.dirname(os.path.abspath(__file__))


def getTimeTable(host='', timeframe='4h', port='8086'):

    loggger.debug("**** START ****")

    nflxu = InfluxUtil(host=host, timeframe=timeframe, port=port)

    # influxCsvResults = influxQuerySimulatedCsv()
    # timeTableResults = calcCiMostRecentTimestampFromCsv(influxCsvResults)
    # influxJsonResults = influxQuerySimulated()

    influxJsonResults = nflxu.influxQuery()

    timeTableResults = nflxu.calcCiMostRecentTimestampFromJson(influxJsonResults)

    loggger.debug("**** timeTableResults ****")
    ciTimeTable = timeTableResults['ciTimeTable']
    for key, prop in ciTimeTable.items():
        _ci        = prop['ci']
        _metricKey = prop['metricKey']
        _timestamp = prop['timestamp']
        _epoch     = prop['epoch']
        print("{} {}  {} : {}".format(_timestamp, _epoch, _ci, _metricKey))
        pass
    pass

    loggger.debug("**** END ****")
    return ciTimeTable
    pass
pass


def handler():

    AWSVARS.dumpEnvironmentVars()

    #PROXY = AWS.proxyUrl
    #INFLUXHOST = AWS.influxHost
    #INFLUXTIMEFRAME = AWSVARS.InfluxQryTimeFrame

    PROXY = ''
    INFLUXHOST = "localhost"
    INFLUXTIMEFRAME = "24h"

    ServiceConfiguration = {"result": {}}
    try:
        ServiceConfiguration = AWS.loadS3File(AWSVARS.s3Bucket_name, AWSVARS.snowFileName, proxy=PROXY)
        #loggger.debug(json.dumps(ServiceConfiguration, indent=4))
    except Exception as E:
        loggger.error("S3 File ERROR: {}".format(str(E)))

    servicesObject = ServiceConfiguration['result'].get('services',{})
    services       = [ (sky, servicesObject[sky]) for sky in servicesObject.keys()]

    service_map = dict()
    for (ci, svc) in services:
        # loggger.debug("**** CI {} ****".format(ci))
        # loggger.debug(json.dumps(svc, indent=4))
        for (source, key, type, )  in  [(svc['panels'][pky]['data_source'], pky, svc['panels'][pky]['metric_type']) for pky in svc['panels'].keys()]:
            loggger.debug("source: {0:16}, type: {3:20}, key: {2:50}, ci: {1} ".format(source, ci, key, type))
            service_map.setdefault(source, {})
            service_map[source].setdefault(ci, dict(type=type, keys=[], ci=ci, source=source))
            service_map[source][ci]["keys"].append(key)
            pass
        pass
    pass
    loggger.debug(json.dumps(service_map, indent=4))

    # ciTimeTable = getTimeTable(host=INFLUXHOST, timeframe=INFLUXTIMEFRAME)
    # loggger.debug(json.dumps(ciTimeTable, indent=4))

    pass
pass


if __name__ == "__main__":

    # Unit test Modules
    loggger.debug("----- START UNIT TEST -----")
    handler()

    loggger.debug("----- END UNIT TEST -----")
