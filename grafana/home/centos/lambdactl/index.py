#!/bin/env python3

import sys
import os
import time
# sys.path.append('.')

from influx_util import InfluxUtil
from aws_util import AwsUtil
from aws_vars import AwsVars


PYTHON = sys.version
AWS = AwsUtil(__name__)
loggger = AWS.loggger
AWSVARS = AwsVars(AWS)

BASE_PATH = os.path.dirname(os.path.abspath(__file__))





def getTimeTable(host='', timeFrame='4h', port='8086'):

    loggger.debug("**** START ****")

    nflxu = InfluxUtil(host=host, timeFrame=timeFrame, port=port)

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
    pass
pass


if __name__ == "__main__":

    # Unit test Modules
    influxHost = "localhost"
    influxTimeFrame = "12h"
    AWSVARS.dumpEnvironmentVars()

    ciTimeTable = getTimeTable(host=influxHost, timeFrame=influxTimeFrame)

    loggger.debug("**** END UNIT TEST ****")

