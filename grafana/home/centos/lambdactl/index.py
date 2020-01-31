#!/bin/env python3

import sys
import os
import json
import copy
import time
import datetime
import re
import uuid

# sys.path.append('.')

from logger_util import LoggerUtil
from influx_util import InfluxUtil
from aws_util import AwsUtil
from aws_vars import AwsVars


PYTHON = sys.version

LOG = LoggerUtil(__name__)
loggger = LOG.loggger

AWS = AwsUtil()
AWSVARS = AwsVars()

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


def handler(event, context):

    ERRORS = 0
    handler_clock_start = time.time()


    #  ----- Build a standard response -----

    response = dict(Status = 'SUCCESS')

    for prop in ['StackId', 'RequestId', 'LogicalResourceId', 'PhysicalResourceId']:
        event.setdefault(prop, '')
        response[prop] = event[prop]
        pass
    pass

    if response['PhysicalResourceId'] == '':
        response['PhysicalResourceId'] = str(uuid.uuid4())
        pass
    pass

    AWSVARS.dumpEnvironmentVars()

    PROXY = AWSVARS.proxyUrl                        # for test: ''
    INFLUXHOST = AWSVARS.influxHost                 # for test: 'localhost'
    INFLUXTIMEFRAME = AWSVARS.influxQryTimeFrame    # for test: '24h'

    nowEpoch = int(time.time())
    nowEpochMinute = epochMinute(nowEpoch)
    intervalSeconds = parsePeriod(INFLUXTIMEFRAME)
    backEpoch = nowEpochMinute - intervalSeconds

    ServiceConfiguration = {"result": {}}
    try:
        ServiceConfiguration = AWS.loadS3File(AWSVARS.s3BucketName, AWSVARS.snowFileName, proxy=PROXY)
        # loggger.debug(json.dumps(ServiceConfiguration, indent=4))
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

        for (_ci, _svc) in services:
            for (_source, _key, _type)  in  [(_svc['panels'][pky]['data_source'], pky, _svc['panels'][pky]['metric_type']) for pky in _svc['panels'].keys()]:
                if _source not in _data_sources:
                    loggger.debug("IGNORED ==> source: {0:16}, type: {3:20}, key: {2:50}, ci: {1} ".format(_source, _ci, _key, _type))
                    continue

                # todo: check why "map"."keys" is not being initialized or erased
                service_map.setdefault(_source, {})
                service_map[_source].setdefault(_ci, dict(config=dict(), map=dict(types=[], keys=[], ci=_ci, source=_source)))

                #service_map[source][_ci].setdefault("map", dict(types=[], keys=[], ci=_ci, source=_source))
                if _type not in service_map[_source][_ci]["map"]["types"]:
                    service_map[_source][_ci]["map"]["types"].append(_type)

                # Keys are already unique within a CI but just in case, avoid dupes
                if _key  not in service_map[_source][_ci]["map"]["keys"]:
                    service_map[_source][_ci]["map"]["keys"].append(_key)

                # From big configuration data, create a small config for this particular source
                service_map[_source][_ci]["config"].setdefault\
                    ("result",
                            {"global": _global,
                             "services": {},
                             "topLevelServices": _topLevelServices,
                             "last_updated": last_updated
                            }
                    )
                _empty_service = {"panels": {} }
                for p in _svc_property_names:
                    _empty_service[p] = _svc[p]

                service_map[_source][_ci]["config"]["result"]["services"].setdefault(_ci, _empty_service)
                # service_map[_source]["config"]["result"]["services"][_ci]["panels"].setdefault(_key, copy.deepcopy(servicesObject[_ci]["panels"][_key]))
                _panel = copy.deepcopy(_svc["panels"][_key])
                service_map[_source][_ci]["config"]["result"]["services"][_ci]["panels"].setdefault(_key, _panel)

                pass
            pass
        pass
        # loggger.debug(json.dumps(service_map, indent=4))
        # print(json.dumps(service_map))


        # Get data from InfluxDB for _source._ci that has keys and types
        for _source in service_map.keys():
            # if _source != 'prometheus':
            #     continue
            for _ci in service_map[_source].keys():
                # if _ci != 'Service Health Portal':
                #     continue
                _types = service_map[_source][_ci]["map"]["types"]
                _keys  = service_map[_source][_ci]["map"]["keys"]
                if _types.__len__() == 0 or _keys.__len__() == 0:
                    del service_map[_source][_ci]
                    continue
                    pass
                pass
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

                #todo: The following statement is erasing the other properties of MAP
                #todo: Should use update.

                service_map[_source][_ci]["map"] = dict(time         =_earlyEpochTime,
                                                      timestamp    =_earlyTimeStamp,
                                                      timeend      = nowEpochMinute,
                                                      timestampend = fmtTimestamp(nowEpochMinute)
                                                    )



        for _source in service_map.keys():
            for _ci in service_map[_source].keys():
                _keys  = service_map[_source][_ci]["map"]["keys"]
                _types = service_map[_source][_ci]["map"]["types"]
                loggger.debug("source: {0:16}, types: {3:20}, key: {2:50}, ci: {1} ".format(_source, _ci, str(_keys), str(_types)))
                pass
            pass
        pass


        # ciTimeTable = getTimeTable(host=INFLUXHOST, timeframe=INFLUXTIMEFRAME)
        # loggger.debug(json.dumps(ciTimeTable, indent=4))

        pass
    pass

    # ============================================================================================
    # ======  SHOW PROCESS STATISTICS  ===========================================================
    # ============================================================================================

    handler_clock_end    = time.time()
    handler_clock_duration = (int(handler_clock_end * 100) - int(handler_clock_start * 100))

    loggger.info("*** START / STOP:   " + str(handler_clock_start)            + " --> " + str(handler_clock_end) + " ***")
    loggger.info("*** CLOCK DURATION: " + str(handler_clock_duration / 100.0) + "  SECONDS ***")

    loggger.info("*** END OF LAMBDA " + response['Status'] + ", ERRORS=" + str(ERRORS))

    #============================================================================================

    return AWS.send_response(event, response)


if __name__ == "__main__":

    # Unit test Modules
    loggger.debug("----- START UNIT TEST -----")
    handler({}, {})

    loggger.debug("----- END UNIT TEST -----")
