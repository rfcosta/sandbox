

from influx_util import InfluxUtil
from aws_util import AwsUtil


AWS = AwsUtil(__name__)
loggger = AWS.loggger

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
    ciTimeTable = getTimeTable()


