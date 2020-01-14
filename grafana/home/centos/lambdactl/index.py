#!/bin/env python3

import sys
import os
# sys.path.append('.')

from influx_util import InfluxUtil
from aws_util import AwsUtil


AWS = AwsUtil(__name__)
loggger = AWS.loggger

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

sqsUrl                      = os.environ['sqsUrl']
s3Bucket_name               = os.environ['s3Bucket_name']
vizAppsFileName             = os.environ['vizAppsFileName']
vizAccountName              = os.environ['vizAccountName']
vizUserName                 = os.environ['vizUserName']
vizAlternateUserName        = os.environ['vizAlternateUserName']
vizEncryptedHash            = os.environ['vizEncryptedHash']
vizAlternateEncryptedHash   = os.environ['vizAlternateEncryptedHash']
vizInstanceName             = os.environ['vizInstanceName']
vizSSO                      = os.environ['vizSSO']
vizURL                      = os.environ['vizURL']

def dumpEnvironmentVars():
    print('DEBUG>> Environment vars:')
    print('DEBUG>> sqsUrl:                    ' + sqsUrl)
    print('DEBUG>> s3Bucket_name:             ' + s3Bucket_name)
    print('DEBUG>> vizAppsFileName:           ' + vizAppsFileName)
    print('DEBUG>> vizAccountName:            ' + vizAccountName)
    print('DEBUG>> vizUserName:               ' + vizUserName)
    print('DEBUG>> vizAlternateUserName:      ' + vizAlternateUserName)
    print('DEBUG>> vizEncryptedHash:          ' + vizEncryptedHash)
    print('DEBUG>> vizAlternateEncryptedHash: ' + vizAlternateEncryptedHash)
    print('DEBUG>> vizInstanceName:           ' + vizInstanceName)
    print('DEBUG>> vizSSO:                    ' + vizSSO)
    print('DEBUG>> vizURL:                    ' + vizURL)

    rightNowLocal = time.localtime()
    rightNowGMT   = time.gmtime()
    print('DEBUG>> nowGMT=' + str(rightNowGMT))
    print('DEBUG>> nowLCL=' + str(rightNowLocal))

    return


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
        _timestamp = prop['timestamp']
        _epoch     = prop['epoch']
        print("{} {}  {}".format(_timestamp, _epoch, _ci))
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
    influxTimeFrame = "4h"
    ciTimeTable = getTimeTable(host=influxHost, timeFrame=influxTimeFrame)

    loggger.debug("**** END UNIT TEST ****")

