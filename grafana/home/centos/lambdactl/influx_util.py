import sys
import os
import json
import datetime
import argparse
import base64
import requests
import re
import copy
import time
#import pytz

from retrying import retry
from aws_util import AwsUtil
from logging  import getLogger, DEBUG, INFO, WARNING, ERROR


sys.path.append('.')

AWS = AwsUtil(__name__)
loggger = AWS.loggger


class InfluxUtil():

    def __init__(self):

        self.TIME_FRAME = os.environ.get("TIME_FRAME", "4h")
        self.INFLUXHOST = "localhost"
        # INFLUXHOST    = "influx-elb-1911.us-east-1.teo.dev.ascint.sabrecirrus.com"
        self.INFLUXPORT = "8086"
        self.url        =  "http://{}:{}/query?db=kpi".format(self.INFLUXHOST, self.INFLUXPORT)
        self.timeout    = 30
        self.timeframe  = self.TIME_FRAME
        self.query = 'SELECT mean("avg_processing_time") AS "mean_avg_processing_time",\
                             mean("error_count")         AS "mean_error_count",\
                             mean("transaction_count")   AS "mean_transaction_count" \
                             FROM "kpi"."days"."metric" \
                             WHERE time > now() - {} \
                             GROUP BY ci, time(1m) \
                             FILL(none)'

        self.no_proxy   = os.environ.get("no_proxy", '')
        self.NO_PROXY   = os.environ.get("NO_PROXY", '')
        self.http_proxy = os.environ.get("http_proxy", '')

        loggger.debug(  "no_proxy: {}".format(self.no_proxy))
        loggger.debug(  "NO_PROXY: {}".format(self.NO_PROXY))
        loggger.debug("http_proxy: {}".format(self.http_proxy))


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
        return str(epoch) + '000000000'


    @retry(stop_max_delay=10000, wait_fixed=2000)
    def influxQuery(self, timeframe = '', url = '', query  = '', timeout = ''):

        _timeframe = timeframe | self.timeframe
        _url       = url       | self.url
        _query     = query     | self.query
        _timeout   = timeout   | self.timeout

        loggger.debug ("******* TIMEFRAME ***** " + timeframe)
        loggger.debug (url)
        loggger.debug (query.format(timeframe))

        _influxQuery = dict(q=_query.format(_timeframe))
        _headers = {'content-type': 'application/json'}

        loggger.debug(json.dumps(_influxQuery, indent=4))


        resp = requests.get(url, params=_influxQuery, headers=_headers, timeout=_timeout)
        if resp.status_code != 200:
            print("Failed: ", resp)
            raise IOError("Error failed to get response from Influx -> " + resp.text)

        influxJsonResponse  = json.loads(resp.content)
        influxResults       = influxJsonResponse['results'][0]
        influxstatement_id  = influxResults["statement_id"]
        influxseries        = influxResults["series"]

        return influxseries


    def calcCiMostRecentTimestampFromJson(self,jsonData):
        ciTimeTable = {}  # Key -> ci
        colDict = {}

        for seriesItem in jsonData: # Series Item contains data for each CI

            # name, tags, columns, values = seriesItem.items()
            # (_, name)    = name
            # (_, tags)    = tags
            # (_, columns) = columns
            # (_, values)  = values

            name    = seriesItem.get('name', '')
            tags    = seriesItem.get('tags', dict())
            _ci     = tags.get("ci", '')
            columns = seriesItem.get('columns', [])
            values  = seriesItem.get('values', [])

            if name != 'metric' or not _ci or len(columns) == 0 or len(values) == 0:
                continue
            pass

            if len(colDict.keys()) == 0:
                for columnIndex, columnName in enumerate(columns):
                    colDict.setdefault(columnIndex, columnName)
                pass
            pass

            for valuerow in values:
                thisRow = {}
                for _colx, _colvalue in enumerate(valuerow):
                    thisRow[colDict[_colx]] = _colvalue
                pass

                _timestamp = thisRow["time"]
                _epoch = self.convert_utc_to_epoch(_timestamp)

                ciTimeTable.setdefault(_ci, dict(ci=_ci, timestamp=_timestamp, epoch=_epoch))

                if _epoch > ciTimeTable[_ci]["epoch"]:
                   ciTimeTable[_ci]["epoch"]     = _epoch
                   ciTimeTable[_ci]["timestamp"] = _timestamp
                pass
            pass

        pass

        return dict(ciTimeTable=ciTimeTable)
    pass



    def calcCiMostRecentTimestampFromCsv(csvData):
        ciTimeTable = {} # Key -> ci

        csvRows = csvData['results']['data']
        for row in csvRows:
            _ci         = row["ci"]
            _timestamp  = row["time"]
            _epoch      = convert_utc_to_epoch(_timestamp)

            ciTimeTable.setdefault(_ci, dict(ci=_ci, timestamp= _timestamp, epoch=_epoch))

            if _epoch > ciTimeTable[_ci]["epoch"]:
                ciTimeTable[_ci]["epoch"]     = _epoch
                ciTimeTable[_ci]["timestamp"] = _timestamp
                pass
            pass
        pass

        return dict(ciTimeTable=ciTimeTable)
        pass
    pass



