#!/bin/env python

import collections
import datetime
import os
import sys
import time

from optparse import OptionParser

import simplejson as json
from influxdb import InfluxDBClient

sys.path.append('/opt/aed/shp/lib')

from service_configuration import ServiceConfiguration
from predictor import Predictor
import shputil

State_Undefined = 'undefined'
State_Staging_No_Alert = 'staging-no-alerting'
State_Staging_Alert = 'staging-alerting'
State_Staging_Validated = 'validated'

SECONDS_IN_MINUTE = 60
MINUTES_TO_KEEP = 4 * SECONDS_IN_MINUTE
MINUTES_TO_CALCULATE = 90
TWO_WEEKS = 60 * 24 * 14

def load_previous_thresholds(cache_id):
    fname = local_thresholds_data_dir + '/' + cache_id + '.json'

    if os.path.isfile(fname):
        with open(fname) as json_file:
            thresholds = json.load(json_file)
    else:
        thresholds = {}
        thresholds['thresholds'] = {}

    return thresholds['thresholds']


def write_new_thresholds(cache_id, thresholds_json):
    fname = local_thresholds_data_dir + '/' + cache_id + '.json'
    # print json.dumps(thresholds_json, indent=4, sort_keys=True)
    with open(fname, 'w') as outfile:
        outfile.write(json.dumps(thresholds_json, indent=4, sort_keys=True))


def remove_seconds(timestamp):
    t = int(int(timestamp) / 60) * 60
    return t


def merge_thresholds(previous, new):
    previous_timestamps = previous.keys()
    new_timestamps = new.keys()

    timestamps_list = []

    add_timestamps_to_list(previous_timestamps, timestamps_list)

    add_timestamps_to_list(new_timestamps, timestamps_list)

    list_len = len(timestamps_list)

    offset = list_len - MINUTES_TO_KEEP
    if offset < 0:
        offset = 0

    timestamps_to_keep = timestamps_list[offset:]

    ordered_keys = collections.OrderedDict()

    for t in sorted(timestamps_to_keep):
        time_str = str(t)

        if time_str in ordered_keys:
            continue

        if time_str in new_timestamps:
            ordered_keys[time_str] = new[time_str]
        else:
            ordered_keys[time_str] = previous[time_str]

    return ordered_keys


def add_timestamps_to_list(timestamps, timestamps_list):
    for t in sorted(timestamps):
        t = t.encode('ascii', 'ignore')
        timestamps_list.append(remove_seconds(t))


def process_thresholds(service_name, metric, key, thresholds, cache_id, need_to_alert):
    previous_thresholds = load_previous_thresholds(cache_id)
    merged_thresholds = merge_thresholds(previous_thresholds, thresholds)

    tags = {}
    tags['need_to_alert'] = need_to_alert
    tags['ci'] = service_name
    tags['metric'] = metric
    tags['key'] = key

    my_json = {}
    my_json['tags'] = tags
    my_json['last_updated'] = get_formatted_timestamp(time.time())
    my_json['thresholds'] = merged_thresholds

    write_new_thresholds(cache_id, my_json)


def get_db_connection():
    influx_host = config['influxdb_host']
    influx_port = config['influxdb_port']
    influx_db = config['influxdb_db']
    return InfluxDBClient(host=influx_host, port=influx_port, database=influx_db)


def get_predictor(service_name, metric, key, standard_deviations, when):
    predictor = None

    timestamp = get_formatted_timestamp(when)

    formatter = "SELECT time, mean({0}) AS {0} FROM {1} WHERE \"key\"='{2}' AND ci='{3}' AND time < '{4}' GROUP BY time(1m) fill(previous)"
    query = formatter.format(metric, metric_db, key, service_name, timestamp)
    # print query

    rs = db_connection.query(query)

    historical_data = []

    for item in rs.items():
        for point in item[1]:
            if None == point[metric]:
                continue
            time = point['time']
            value = point[metric]
            single_tuple = (time, value)
            historical_data.append(single_tuple)

    if len(historical_data) < TWO_WEEKS:
        raise Exception("Not enough data to analyze for: ", service_name, '-', key)

    predictor = Predictor(metric, historical_data, standard_deviations, MINUTES_TO_CALCULATE)

    return predictor


def calculate_dynamic_thresholds(service_config, service_name, when):
    service = service_config.get_service(service_name)

    state = service.state

    for panel in service.panels:
        try:
            metric = panel.metric_type

            key = panel.panelKey

            cache_id = service_name + '-' + metric + '-' + key
            cache_id = cache_id.replace('/', ' ')
            print "ID:", cache_id

            standard_deviations = panel.thresholds.standard_deviations

            predictor = get_predictor(service_name, metric, key, standard_deviations, when)

            dynamic_thresholds = predictor.predict()

            display_state = panel.display_state
            dynamic_alerting_enabled = panel.dynamic_alerting_enabled
            need_to_alert = dynamic_alerting_enabled == 'true' and display_state == 'Active' and state != State_Undefined and state != State_Staging_No_Alert

            i = 0

            computed_thresholds = {}

            for thresholds in zip(dynamic_thresholds[0], dynamic_thresholds[1]):
                limits = {}
                limits['lower'] = thresholds[0]
                limits['upper'] = thresholds[1]
                computed_thresholds[str(remove_seconds(when + i))] = limits
                i += SECONDS_IN_MINUTE

            process_thresholds(service_name, metric, key, computed_thresholds, cache_id, need_to_alert)
        except Exception as e:
            print str(e)


def get_formatted_timestamp(when):
    fmt = "%Y-%m-%d %H:%M:00"
    t = datetime.datetime.fromtimestamp(float(when))
    return t.strftime(fmt)

parser = OptionParser()
parser.add_option("--service_name", dest="service_name", default="")
(options, args) = parser.parse_args()

service_name = options.service_name

if not service_name:
    raise Exception("missing --service_name argument")

config = shputil.get_config()

when = int(time.time())

db_connection = get_db_connection()

service_config = ServiceConfiguration()

metric_db = config['influxdb_metric_policy'] + '.' + config['influxdb_metric_measure']

local_data_dir = config['local_dynamic_thresholds_dir']
local_thresholds_data_dir = local_data_dir + '/threshold_history'

if not os.path.isdir(local_data_dir):
    os.mkdir(local_data_dir, 0777)

if not os.path.isdir(local_thresholds_data_dir):
    os.mkdir(local_thresholds_data_dir, 0777)

calculate_dynamic_thresholds(service_config, service_name, when)

db_connection.close()
