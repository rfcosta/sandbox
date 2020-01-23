#!/bin/env python3

import sys
import os
import json
import copy
import time
import datetime
import re

# sys.path.append('.')

from influx_util import InfluxUtil
from aws_util import AwsUtil
from aws_vars import AwsVars


PYTHON = sys.version
AWS = AwsUtil(__name__)
loggger = AWS.loggger
AWSVARS = AwsVars(AWS)

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

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


def getTimeTable(host='', timeframe='4h', port='8086',
                 types=["avg_processing_time","error_count","transaction_count"], ci=''):

    nflxu = InfluxUtil(host=host, timeframe=timeframe, port=port, types=types, ci=ci)

    loggger.debug(nflxu.getSqlQuery())

    # influxCsvResults = influxQuerySimulatedCsv()
    # timeTableResults = calcCiMostRecentTimestampFromCsv(influxCsvResults)
    # influxJsonResults = influxQuerySimulated()

    influxJsonResults = nflxu.influxQuery()

    timeTableResults = nflxu.calcCiMostRecentTimestampFromJson(influxJsonResults)

    loggger.debug("**** timeTableResults ****")
    ciTimeTable = timeTableResults['ciTimeTable']
    for _ci, _keyDict in ciTimeTable.items():
        for _key, _dataPoint in _keyDict.items():
            _timestamp = _dataPoint['timestamp']
            _epoch     = _dataPoint['epoch']
            _value     = _dataPoint['value']

            loggger.debug("{} {}  {} : {} = {}".format(_timestamp, str(_epoch), _ci, _key, str(_value)))
            pass
        pass
    pass

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

    nowEpoch = int(time.time())
    nowEpochMinute = epochMinute(nowEpoch)
    intervalSeconds = parsePeriod(INFLUXTIMEFRAME)
    backEpoch = nowEpochMinute - intervalSeconds

    ServiceConfiguration = {"result": {}}
    try:
        ServiceConfiguration = AWS.loadS3File(AWSVARS.s3Bucket_name, AWSVARS.snowFileName, proxy=PROXY)
        loggger.debug(json.dumps(ServiceConfiguration, indent=4))
    except Exception as E:
        loggger.error("S3 File ERROR: {}".format(str(E)))

    servicesObject = ServiceConfiguration['result'].get('services',{})

    if servicesObject.keys().__len__() > 0:
        services       = [ (sky, servicesObject[sky]) for sky in servicesObject.keys()]

        # Create a service map dictionary grouping all by source, ci
        service_map = dict()
        last_updated = ServiceConfiguration["result"]["last_updated"]
        _global           = copy.deepcopy(ServiceConfiguration['result']["global"])
        _topLevelServices = [copy.deepcopy(x) for x in ServiceConfiguration["result"]["topLevelServices"]]
        _svc_property_names = ["state","knowledge_article","report_grouping","service_config_sys_id","uid"]
        _data_sources = ["prometheus", "viz", "zabbix"]

        for (ci, svc) in services:
            #loggger.debug("SVC ==> " + json.dumps(svc, indent=4))
            for (source, key, type)  in  [(svc['panels'][pky]['data_source'], pky, svc['panels'][pky]['metric_type']) for pky in svc['panels'].keys()]:
                if source not in _data_sources:
                    continue

                loggger.debug("source: {0:16}, type: {3:20}, key: {2:50}, ci: {1} ".format(source, ci, key, type))

                service_map.setdefault(source, {})
                service_map[source].setdefault(ci, dict(config=dict(), map=dict(types=[], keys=[], ci=ci, source=source)))
                #service_map[source][ci].setdefault("map", dict(types=[], keys=[], ci=ci, source=source))
                if type not in service_map[source][ci]["map"]["types"]:
                    service_map[source][ci]["map"]["types"].append(type)
                service_map[source][ci]["map"]["keys"].append(key)

                # From big configuration data, create a small config for this particular source
                service_map[source][ci]["config"].setdefault\
                    ("result",
                            {"global": _global,
                             "services": {},
                             "topLevelServices": _topLevelServices,
                             "last_updated": last_updated
                            }
                    )
                _empty_service = {"panels": {} }
                for p in _svc_property_names:
                    _empty_service[p] = svc[p]

                service_map[source][ci]["config"]["result"]["services"].setdefault(ci, _empty_service)
                # service_map[source]["config"]["result"]["services"][ci]["panels"].setdefault(key, copy.deepcopy(servicesObject[ci]["panels"][key]))
                _panel = copy.deepcopy(svc["panels"][key])
                service_map[source][ci]["config"]["result"]["services"][ci]["panels"].setdefault(key, _panel)

                pass
            pass
        pass
        # loggger.debug(json.dumps(service_map, indent=4))
        # print(json.dumps(service_map))

        for _type in service_map.keys():
            if _type != 'prometheus':
                continue
            for _ci in service_map[_type].keys():
                if _ci != 'Service Health Portal':
                    continue
                _types = service_map[_type][_ci]["map"]["types"]
                _keys  = service_map[_type][_ci]["map"]["keys"]
                _ciTimeTable = getTimeTable(host=INFLUXHOST, timeframe=INFLUXTIMEFRAME, ci=_ci, types=_types)
                loggger.debug("CI: {}, TimeTable: {}".format(_ci, json.dumps(_ciTimeTable)))

                _earlyEpochTime = backEpoch
                _earlyTimeStamp = fmtTimestamp(_earlyEpochTime)
                _earlyValue     = 0

                _timeTableCi = _ciTimeTable.get(_ci)
                if _timeTableCi:
                    # Find earliest minute
                    for _key in _ciTimeTable[_ci].keys():
                        if _ciTimeTable[_ci][_key]["epoch"] > _earlyEpochTime:
                            _earlyEpochTime = _ciTimeTable[_ci][_key]["epoch"]
                            _earlyTimeStamp = _ciTimeTable[_ci][_key]["timestamp"]
                            _earlyValue     = _ciTimeTable[_ci][_key]["value"]
                        pass
                    pass
                pass

                service_map[_type][_ci]["map"] = dict(time         =_earlyEpochTime,
                                                      timestamp    =_earlyTimeStamp,
                                                      timeend      = nowEpochMinute,
                                                      timestampend = fmtTimestamp(nowEpochMinute)
                                                    )



        for _source in service_map.keys():
            for _ci in service_map[_source].keys():
                _keys  = service_map[_type][_ci]["map"]["keys"]
                _types = service_map[_type][_ci]["map"]["types"]
                loggger.debug("source: {0:16}, types: {3:20}, key: {2:50}, ci: {1} ".format(_source, _ci, str(_keys), str(_types)))
                pass
            pass
        pass


        # ciTimeTable = getTimeTable(host=INFLUXHOST, timeframe=INFLUXTIMEFRAME)
        # loggger.debug(json.dumps(ciTimeTable, indent=4))

        pass
    pass


if __name__ == "__main__":

    # Unit test Modules
    loggger.debug("----- START UNIT TEST -----")
    handler()

    loggger.debug("----- END UNIT TEST -----")
