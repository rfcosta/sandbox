#!/bin/env python3

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
from seasonality import Seasonality

import shputil

State_Undefined = 'undefined'
State_Staging_No_Alert = 'staging-no-alerting'
State_Staging_Alert = 'staging-alerting'
State_Staging_Validated = 'validated'

SECONDS_IN_MINUTE = 60
MINUTES_TO_KEEP = 4 * SECONDS_IN_MINUTE
MINUTES_TO_PREDICT = 90
TWO_WEEKS = 60 * 24 * 14
ONE_WEEK_IN_SECONDS = 60 * 60 * 24 * 7

MAX_SEASONS_CACHE_AGE = ONE_WEEK_IN_SECONDS

MAX_DEVIATIONS = 6
MIN_DEVIATIONS = 1


def get_db_connection():
    influx_host = config['influxdb_host']
    influx_port = config['influxdb_port']
    influx_db = config['influxdb_db']
    return InfluxDBClient(host=influx_host, port=influx_port, database=influx_db)


def get_formatted_timestamp(when):
    fmt = "%Y-%m-%d %H:%M:00"
    t = datetime.datetime.fromtimestamp(float(when))
    return t.strftime(fmt)


def remove_seconds(timestamp):
    t = int(int(timestamp) / 60) * 60
    return t


def get_cache_id(service_name, metric, key):
    cache_id = service_name + '-' + metric + '-' + key
    cache_id = cache_id.replace('/', ' ')
    return cache_id


def add_timestamps_to_list(timestamps, timestamps_list):
    for t in sorted(timestamps):
        t = t.encode('ascii', 'ignore')
        timestamps_list.append(remove_seconds(t))


def load_previous_thresholds(cache_id):
    fname = local_thresholds_data_dir + '/' + cache_id + '.json'

    if os.path.isfile(fname):
        with open(fname) as json_file:
            thresholds = json.load(json_file)
    else:
        thresholds = {'thresholds': {}}

    return thresholds['thresholds']


def write_new_thresholds(cache_id, thresholds_json):
    fname = local_thresholds_data_dir + '/' + cache_id + '.json'
    # logger.debug(json.dumps(thresholds_json, indent=4, sort_keys=True))
    with open(fname, 'w') as outfile:
        outfile.write(json.dumps(thresholds_json, indent=4, sort_keys=True))


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


def process_thresholds(service_name, metric, key, thresholds, cache_id):
    previous_thresholds = load_previous_thresholds(cache_id)
    merged_thresholds = merge_thresholds(previous_thresholds, thresholds)

    tags = {'ci': service_name, 'metric': metric, 'key': key}

    my_json = {'tags': tags, 'last_updated': get_formatted_timestamp(time.time()), 'thresholds': merged_thresholds}

    write_new_thresholds(cache_id, my_json)


def load_historical_data(key, metric, service_name, to_when):
    to_time = get_formatted_timestamp(to_when)
    historical_data = []
    formatter = "SELECT time, mean({0}) AS {0} FROM {1} WHERE \"key\"='{2}' AND ci='{3}' AND time < '{4}' GROUP BY time(1m) fill(previous)"
    query = formatter.format(metric, metric_db, key, service_name, to_time)
    rs = db_connection.query(query)
    for item in rs.items():
        for point in item[1]:
            if point[metric] is None:
                continue
            time = point['time']
            value = point[metric]
            single_tuple = (time, value)
            historical_data.append(single_tuple)

    if len(historical_data) < TWO_WEEKS:
        raise RuntimeWarning("Not enough data to analyze for: " + service_name + '-' + key)

    return historical_data


def get_predictor(service_name, metric, key, standard_deviations, seasonal_periods, when):
    historical_data = load_historical_data(key, metric, service_name, when)
    return Predictor(metric, historical_data, seasonal_periods, standard_deviations, MINUTES_TO_PREDICT)


def save_seasons(cache_id, seasons):
    fname = local_thresholds_data_dir + '/' + cache_id + '-seasons.json'

    season_json = {'seasons': seasons, 'last_updated': get_formatted_timestamp(time.time())}

    with open(fname, 'w') as outfile:
        outfile.write(json.dumps(season_json, indent=4, sort_keys=True))


def get_seasons(service_name, metric, key, when):
    cache_id = get_cache_id(service_name, metric, key)
    fname = local_thresholds_data_dir + '/' + cache_id + '-seasons.json'

    seasons = None
    if os.path.isfile(fname):
        with open(fname) as json_file:
            seasons = json.load(json_file)
            seasons = seasons['seasons']
            logger.debug(service_name + " - Loaded Seasons From Cache: " + str(seasons))

    if seasons is None:
        logger.debug(service_name + " - Seasons not found in cache - recomputing")
        historical_data = load_historical_data(key, metric, service_name, when)
        seasons = Seasonality(historical_data).get_seasons()
        logger.info(service_name + " - Seasonality: " + str(seasons))
        save_seasons(cache_id, seasons)

    return seasons


def get_standard_deviations(service_config, service_name, configured_standard_deviations):
    try:
        deviations_adjustment = service_config.dynamic_alerting_deviations_adjustment
        standard_deviations = configured_standard_deviations + int(deviations_adjustment)
    except:
        logger.debug(service_name + " - dynamic_alerting_deviations_adjustment is invalid: " + str(deviations_adjustment))
        standard_deviations = configured_standard_deviations

    if standard_deviations > MAX_DEVIATIONS:
        logger.debug(service_name + " - " + str(standard_deviations) + "> MAX_DEVIATIONS - Using " + str(MAX_DEVIATIONS))
        standard_deviations = MAX_DEVIATIONS

    if standard_deviations < MIN_DEVIATIONS:
        logger.debug(service_name + " - " + str(standard_deviations) + "<  MIN_DEVIATIONS - Using " + str(MIN_DEVIATIONS))
        standard_deviations = MIN_DEVIATIONS

    if standard_deviations != configured_standard_deviations:
        logger.debug(service_name + " - Using modified number of deviations:", standard_deviations, " was ", configured_standard_deviations)
    else:
        logger.debug(service_name + " - Using configured number of deviations: " + str(standard_deviations))

    return standard_deviations


def calculate_dynamic_thresholds(service_config, service_name, when):
    service = service_config.get_service(service_name)

    try:
        for panel in service.panels:
            metric = panel.metric_type

            key = panel.panelKey

            cache_id = get_cache_id(service_name, metric, key)

            standard_deviations = get_standard_deviations(service_config, service_name, panel.thresholds.standard_deviations)
            seasonal_periods = get_seasons(service_name, metric, key, when)
            predictor = get_predictor(service_name, metric, key, standard_deviations, seasonal_periods, when)
            dynamic_thresholds = predictor.predict()

            i = 0
            computed_thresholds = {}

            for thresholds in zip(dynamic_thresholds[0], dynamic_thresholds[1]):
                limits = {
                    'lower': round(thresholds[0], 2),
                    'upper': round(thresholds[1], 2)
                }
                computed_thresholds[str(remove_seconds(when + i))] = limits
                i += SECONDS_IN_MINUTE

            process_thresholds(service_name, metric, key, computed_thresholds, cache_id)
    except RuntimeWarning as runtimeWarning:
        logger.info(runtimeWarning)

    except Exception as e:
        logger.exception(e)


# Main

parser = OptionParser()
parser.add_option("--service_name", dest="service_name", default="")
(options, args) = parser.parse_args()

service_name = options.service_name

if not service_name:
    raise Exception("missing --service_name argument")

config = shputil.get_config()

logger = shputil.get_logger("dynamicThresholds")

when = int(time.time())

db_connection = get_db_connection()

service_config = ServiceConfiguration()

metric_db = config['influxdb_metric_policy'] + '.' + config['influxdb_metric_measure']

local_data_dir = config['local_dynamic_thresholds_dir']
local_thresholds_data_dir = local_data_dir + '/threshold_history'

if not os.path.isdir(local_data_dir):
    os.mkdir(local_data_dir, 0o777)

if not os.path.isdir(local_thresholds_data_dir):
    os.mkdir(local_thresholds_data_dir, 0o777)

calculate_dynamic_thresholds(service_config, service_name, when)

db_connection.close()