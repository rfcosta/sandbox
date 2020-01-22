import os
import sys
import time
import datetime
import re


sys.path.append('/Users/sg0549743/_github/influxdata/grafana/home/centos/lambdactl')

from aws_util import AwsUtil

AWS = AwsUtil(__name__)
loggger = AWS.loggger

def epoch2date(self, epoch):
    return datetime.datetime.fromtimestamp(float(epoch))


def epochMinute(epoch):
    return int(epoch) // 60 * 60


def nowMinute():
    pass

def fmtTimestamp(epoch):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(epoch))

def parsePeriod(pstr):
    if pstr.isdigit():
        return int(pstr)

    number, unit = [60, 's']
    tokens = _XINTERVAL.match(pstr)
    if tokens:
        number, unit = tokens.groups()
        if number:
            number = int(number)
        if not unit:
            unit = 's'
        secondsInUnit = _UNITS.get(unit, 1)
    else:
        number = 60
        secondsInUnit = 1
    pass

    intervalSeconds = number * secondsInUnit

    loggger.debug("Interval %s, number %s, secondsInUnit %d, result: %d"
                  % (pstr, str(number), secondsInUnit, intervalSeconds)
                  )

    return intervalSeconds


timeframe = "4h"

_XINTERVAL = re.compile("(\d+)([smhdw]*)")
_UNITS = dict(s=1
            , m=60
            , h=60 * 60
            , d=60 * 60 * 24
            , w=60 * 60 * 24 * 7
            )

nowEpoch = int(time.time())
nowEpochMinute = epochMinute(nowEpoch)
intervalSeconds = parsePeriod(timeframe)
backEpoch = nowEpochMinute - intervalSeconds

loggger.info("timeframe:       {}".format(timeframe))
loggger.info("nowEpoch:        {} {}".format(nowEpoch, fmtTimestamp(nowEpoch)))
loggger.info("nowEpochMinute:  {} {}".format(nowEpochMinute, fmtTimestamp(nowEpochMinute)))
loggger.info("intervalSeconds: {}".format(intervalSeconds))
loggger.info("backEpoch:       {} {}".format(backEpoch, fmtTimestamp(backEpoch)))




