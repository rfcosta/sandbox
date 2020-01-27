import sys
import os
import json
import requests
import time
import re
import datetime

# import argparse
# import base64
# import copy
# #import pytz
# from logging  import getLogger, DEBUG, INFO, WARNING, ERROR

from retrying import retry


sys.path.append('.')

from logger_util import LoggerUtil


LOG = LoggerUtil(__name__)
loggger = LOG.loggger

class InfluxUtil:

    #todo: Query needs to be built from all given metrics for that dashboard ? What happens with dashboards with multiple error_count for example?

    def __init__(self, host='', timeframe='4h', port='8086', timeout=10,
                 types=["avg_processing_time","error_count","transaction_count"], ci='Service Health Portal'):


        self.ci = ci
        self.types = types

        self.http_proxy = 'www-ad-proxy.sabre.com'
        self.TIME_FRAME = os.environ.get("TIME_FRAME", timeframe)
        self.INFLUXHOST = host  or "localhost"
        # INFLUXHOST    = "influx-elb-1911.us-east-1.teo.dev.ascint.sabrecirrus.com"
        self.INFLUXPORT = port
        self.url = "http://{}:{}/query?db=kpi".format(self.INFLUXHOST, self.INFLUXPORT)
        self.timeout = timeout
        self.timeframe  = self.TIME_FRAME


        self.old_query = 'SELECT mean("avg_processing_time") AS "mean_avg_processing_time",\
                             mean("error_count")         AS "mean_error_count",\
                             mean("transaction_count")   AS "mean_transaction_count" \
                             FROM "kpi"."days"."metric" \
                             WHERE time > now() - {} \
                             GROUP BY ci, key, type time(1m) \
                             FILL(none)'

        self.static_query = 'SELECT mean("avg_processing_time") AS "mean_avg_processing_time", \
                             mean("count")               AS "mean_count", \
                             mean("error_count")         AS "mean_error_count", \
                             mean("error_rate")          AS "mean_error_rate", \
                             mean("transaction_count")   AS "mean_transaction_count" \
                             FROM "kpi"."days"."metric" \
                             WHERE time > now() - {} \
                             AND   time < now() \
                             GROUP BY "source", "ci", "key", time(1m) \
                             FILL(none)'

        _typesQuery = ", ".join(['mean("{}") AS "{}"'.format(t,t) for t in types])
        self.query = 'SELECT {} FROM "kpi"."days"."metric" WHERE time > now() - {} AND time < now() AND "ci" = \'{}\' \
                        GROUP BY "source", "ci", "key", time(1m) \
                        FILL(none)'.format( _typesQuery, "{}", ci )

        self.no_proxy = os.environ.get("no_proxy", '')
        self.NO_PROXY = os.environ.get("NO_PROXY", '')
        self.http_proxy = os.environ.get("http_proxy", '')

        loggger.debug("no_proxy:        {}".format(self.no_proxy))
        loggger.debug("NO_PROXY:        {}".format(self.NO_PROXY))
        loggger.debug("http_proxy:      {}".format(self.http_proxy))

        self.loggger = loggger

    def getSqlQuery(self):
        return self.query

    @staticmethod
    def load_file(filename):
        try:
            with open(filename) as query_file:
                return json.load(query_file)
        except ValueError as err:
            raise err

    @staticmethod
    def convert_utc_to_epoch(timestamp_string):
        '''Use this function to convert utc to epoch'''
        from datetime import datetime
        import calendar

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
        return epoch


    @retry(stop_max_delay=10000, wait_fixed=2000)
    def influxQuery(self, timeframe = '', url = '', query  = '', timeout = ''):

        _timeframe = timeframe or self.timeframe
        _url = url or self.url
        _query = query or self.query
        _timeout = timeout or self.timeout

        loggger.debug ("******* TIMEFRAME ***** " + timeframe)
        loggger.debug (url)
        loggger.debug (query.format(timeframe))

        _influxQuery = dict(q=_query.format(_timeframe))
        _headers = {'content-type': 'application/json'}

        loggger.debug(json.dumps(_influxQuery, indent=4))


        resp = requests.get(_url, params=_influxQuery, headers=_headers, timeout=_timeout)
        if resp.status_code != 200:
            print("Failed: ", resp)
            raise IOError("Error failed to get response from Influx -> " + resp.text)

        influxJsonResponse  = json.loads(resp.content)
        influxResults       = influxJsonResponse['results'][0]
        influxstatement_id  = influxResults["statement_id"]
        influxseries        = influxResults.get("series", [])  # Empty if no data

        return influxseries


    def calcCiMostRecentTimestampFromJson(self,jsonData):

        #loggger.debug(json.dumps(jsonData, indent=4))
        colDict = {}

        ciTimeTable = {}  # [ci] [key]

        for seriesItem in jsonData: # Series Item contains data for each CI

            # name, tags, columns, values = seriesItem.items()
            # (_, name)    = name
            # (_, tags)    = tags
            # (_, columns) = columns
            # (_, values)  = values

            name    = seriesItem.get('name', '')
            tags    = seriesItem.get('tags', dict())
            _ci     = tags.get("ci", '')
            _key    = tags.get("key", '')
            columns = seriesItem.get('columns', [])
            values  = seriesItem.get('values', [])

            if name != 'metric' or not _ci or len(columns) == 0 or len(values) == 0:
                continue
            pass

            if len(colDict.keys()) == 0:
                # Build table of column index -> columns names
                for columnIndex, columnName in enumerate(columns):
                    colDict.setdefault(columnIndex, columnName)
                pass
            pass

            loggger.debug(json.dumps(colDict, indent=4))

            for valuerow in values:
                thisRow = {}
                for _colx, _colvalue in enumerate(valuerow):
                    if _colx == 0:
                        thisRow[colDict[_colx]] = _colvalue

                    if type( _colvalue )  == 'None':
                        pass
                    else:
                        thisRow['value'] = _colvalue
                        pass
                    pass
                pass

                loggger.debug(json.dumps(thisRow, indent=4))

                for _col in thisRow.keys():
                    if _col == "time":
                        continue
                    _timestamp = thisRow["time"]
                    _value     = thisRow["value"]
                    _epoch = self.convert_utc_to_epoch(_timestamp)

                    ciTimeTable.setdefault(_ci, dict())
                    ciTimeTable[_ci].setdefault(_key, dict(ci=_ci, key=_key, timestamp=_timestamp, epoch=_epoch, value=_value))

                    if _epoch > ciTimeTable[_ci][_key]["epoch"]:
                        ciTimeTable[_ci][_key]["epoch"]     = _epoch
                        ciTimeTable[_ci][_key]["timestamp"] = _timestamp
                        ciTimeTable[_ci][_key]["value"]     = _value
                    pass
            pass

        pass

        loggger.debug(json.dumps(ciTimeTable, indent=4))
        return dict(ciTimeTable=ciTimeTable)
    pass

    def calMostRecentTimestampOfCi(self):
        pass

    def calcCiMostRecentTimestampFromCsv(self,csvData):
        ciTimeTable = {} # Key -> ci

        csvRows = csvData['results']['data']
        for row in csvRows:
            _ci         = row["ci"]
            _timestamp  = row["time"]
            _epoch      = self.convert_utc_to_epoch(_timestamp)

            ciTimeTable.setdefault(_ci, dict(ci=_ci, timestamp= _timestamp, epoch=_epoch))

            if _epoch > ciTimeTable[_ci]["epoch"]:
                ciTimeTable[_ci]["epoch"]     = _epoch
                ciTimeTable[_ci]["timestamp"] = _timestamp
                pass
            pass
        pass

        loggger.debug(json.dumps(dict(ciTimeTable=ciTimeTable), indent=4))

        return dict(ciTimeTable=ciTimeTable)
        pass
    pass



