import datetime
import sys

import numpy as np
from influxdb import InfluxDBClient

sys.path.append('/opt/aed/shp/lib')
import shputil


class StandardDeviation:
    MINUTES_IN_WEEK = 60 * 24 * 7
    NUMBER_OF_STDDEV = 2

    lags = [60, 1436, 1437, 1438, 1439, 1440, 1441, 1442, 1443, 1444, MINUTES_IN_WEEK, int(MINUTES_IN_WEEK * 2)]

    def __init__(self, trained_model, service_name, metric, key):
        self.service_name = service_name.replace(' ', '-')
        self.metric = metric
        self.key = key
        self.trained_model = trained_model
        config = shputil.get_config()
        self.influx_host = config['influxdb_host']
        self.influx_port = config['influxdb_port']
        self.influx_db = config['influxdb_db'] + ".\"" + config['influxdb_metric_policy'] + "\"." + \
                         config['influxdb_metric_measure']
        self.db_connection = InfluxDBClient(host=self.influx_host, port=self.influx_port, database=self.influx_db)

    @staticmethod
    def get_formatted_timestamp(when):
        fmt = "%Y-%m-%d %H:%M:00"
        t = datetime.datetime.fromtimestamp(float(when))
        return t.strftime(fmt)


    def calculate_standard_deviation(self, when):
        data = []
        values = [data]

        for lag in self.lags:
            query = 'SELECT time, ' + self.metric + ' FROM ' + self.influx_db + ' WHERE "key"=\'' + self.key + '\' AND ci=\'' + self.service_name + '\' AND time > \'' + self.get_formatted_timestamp(
                when) + '\' - ' + str(lag) + 'm limit 1'

            rs = self.db_connection.query(query)
            for item in rs.items():
                for point in item[1]:
                    values[0].append(point[self.metric])

        predicted_value = self.trained_model.lgbRegr.predict(values)

        sd = np.std(self.trained_model.get_trainY())

        self.upper_limit = predicted_value + (self.NUMBER_OF_STDDEV * sd)
        self.lower_limit = predicted_value - (self.NUMBER_OF_STDDEV * sd)

        if self.lower_limit[0] < 0:
            self.lower_limit[0] = 0


    def get_lower_limit(self):
        return self.lower_limit[0]


    def get_upper_limit(self):
        return self.upper_limit[0]
