
import sys
import os
import json
import copy
import time
import datetime
import re




class ServiceQueue():


    def __init__(self, serviceConfig):
        pass



    # Utility functions
    # =================

    _XINTERVAL = re.compile("(\d+)([smhdw]*)")
    _UNITS = dict(s=1
                  , m=60
                  , h=60 * 60
                  , d=60 * 60 * 24
                  , w=60 * 60 * 24 * 7
                  )
    def epoch2date(epoch):
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

