#!/bin/python3

import json
import requests
import os

from retrying import retry

import sys

print('Python %s on %s' % (sys.version, sys.platform))
TIME_FRAME = os.environ.get("TIME_FRAME", "4h")

no_proxy = os.environ.get("no_proxy",'')
NO_PROXY = os.environ.get("NO_PROXY",'')
http_proxy = os.environ.get("http_proxy",'')

print("no_proxy: {}".format(no_proxy))
print("NO_PROXY: {}".format(NO_PROXY))
print("http_proxy: {}".format(http_proxy))

INFLUXHOST = "localhost"
#INFLUXHOST = "influx-elb-1911.us-east-1.teo.dev.ascint.sabrecirrus.com"
INFLUXPORT = "8086"


DEFAULTS = dict(url       = "http://{}:{}/query?db=kpi".format(INFLUXHOST, INFLUXPORT),
                timeout   = 30,
                timeframe = TIME_FRAME,
                query     = 'SELECT mean("avg_processing_time") AS "mean_avg_processing_time", mean("error_count") AS "mean_error_count", mean("transaction_count") AS "mean_transaction_count" FROM "kpi"."days"."metric" WHERE time > now() - {} GROUP BY ci, time(1m) FILL(none)',
                )

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
def influxQuery(timeframe   = DEFAULTS['timeframe'], # 1h
                url         = DEFAULTS['url'],
                query       = DEFAULTS['query'],
                timeout     = DEFAULTS['timeout']
                ):

    print ("******* TIMEFRAME ***** " + timeframe)
    print (url)
    print (query.format(timeframe))

    influxQuery = dict(q=query.format(timeframe))
    headers = {'content-type': 'application/json'}

    print(json.dumps(influxQuery, indent=4))


    resp = requests.get(url, params=influxQuery, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        print("Failed: ", resp)
        raise IOError("Error failed to get response from Influx -> " + resp.text)

    influxJsonResponse = json.loads(resp.content)
    influxResults       = influxJsonResponse['results'][0]
    influxstatement_id  = influxResults["statement_id"]
    influxseries        = influxResults.get("series", {})

    return influxseries


def calcCiMostRecentTimestampFromJson(jsonData):
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
            _epoch = convert_utc_to_epoch(_timestamp)

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




if __name__ == "__main__":
    print("**** START ****")

    # influxCsvResults = influxQuerySimulatedCsv()
    # timeTableResults = calcCiMostRecentTimestampFromCsv(influxCsvResults)
    # influxJsonResults = influxQuerySimulated()

    influxJsonResults = influxQuery()

    timeTableResults = calcCiMostRecentTimestampFromJson(influxJsonResults)
    print("**** timeTableResults ****")
    #print(json.dumps(timeTableResults, indent=4))

    ciTimeTable = timeTableResults['ciTimeTable']
    for key, prop in ciTimeTable.items():
        _ci        = prop['ci']
        _timestamp = prop['timestamp']
        _epoch     = prop['epoch']
        print("{} {}  {}".format(_timestamp, _epoch, _ci))
        pass
    pass

    print("**** END ****")
    pass
pass


