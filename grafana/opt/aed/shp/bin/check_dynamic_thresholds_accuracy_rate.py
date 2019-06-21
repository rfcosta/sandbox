#!/bin/env python

import datetime
import sys
import time

from influxdb import InfluxDBClient

sys.path.append('/opt/aed/shp/lib')

from service_configuration import ServiceConfiguration
import shputil

from predictor import Predictor

MINUTES_IN_HOUR = 60
MINUTES_IN_DAY = MINUTES_IN_HOUR * 24

DAYS_TO_SCAN = 8
MIN_POINTS =  (DAYS_TO_SCAN * MINUTES_IN_DAY) * .5
MIN_THRESHOLDS =  (DAYS_TO_SCAN * MINUTES_IN_DAY)

total_panels = 0
panels_not_validated = 0
panels_lacking_data = 0
already_enabled = 0
ready_to_enable = 0

def get_db_connection():
    influx_host = config['influxdb_host']
    influx_port = config['influxdb_port']
    influx_db = config['influxdb_db']
    return InfluxDBClient(host=influx_host, port=influx_port, database=influx_db)


def get_recent_thresholds(metric, key, service_name, timestamp):
    formatter = "SELECT time, mean({0}_crit_lower) as crit_lower, mean({0}_crit_upper) as crit_upper FROM {1} WHERE \"key\"='{2}' AND ci='{3}' AND time > '{4}' AND type='dynamic' GROUP BY time(1m) fill(previous)"
    query = formatter.format(metric, threshold_db, key, service_name, timestamp)

    recent_thresholds = {}
    rs = db_connection.query(query)
    for item in rs.items():
        for point in item[1]:
            recent_thresholds[point['time']] = point

    return recent_thresholds


def get_recent_metrics(metric, key, service_name, timestamp):
    formatter = "SELECT time, percentile({0}, 95) AS {0} FROM {1} WHERE \"key\"='{2}' AND ci='{3}' AND time > '{4}' GROUP BY time(1m) fill(none)"
    formatter = "SELECT time, max({0}) AS {0} FROM {1} WHERE \"key\"='{2}' AND ci='{3}' AND time > '{4}' GROUP BY time(1m) fill(none)"
    query = formatter.format(metric, metric_db, key, service_name, timestamp)
    #print query

    recent_metrics = []
    rs = db_connection.query(query)
    for item in rs.items():
        for point in item[1]:
#            print "POINT:", point
            recent_metrics.append(point)

    return recent_metrics


def count_alerts(service_name, metric_name, key, when, panel):
    global panels_lacking_data
    global ready_to_enable

    then = when - ((MINUTES_IN_DAY * DAYS_TO_SCAN) * 60)
    timestamp = get_formatted_timestamp(then)

    thresholds = get_recent_thresholds(metric_name, key, service_name, timestamp)
    if (len(thresholds) < MIN_THRESHOLDS):
       panels_lacking_data = panels_lacking_data + 1
       print service_name, ':', key, ':', metric_name,  MIN_THRESHOLDS, ": Total Alerts: Insufficient predictions"
       return

    metrics = get_recent_metrics(metric_name, key, service_name, timestamp)

    #window = panel.threshold_violation_window.encode('ascii','ignore')
    window = 5
    #occurrences = panel.threshold_violation_occurrences.encode('ascii','ignore')
    occurrences = 5

#    print "WINDOW: ", window, "OCCURRENCES: ", occurrences

    alerts = []

    bad_total = 0

    i = 0
    total_compared = 0
    for metric in metrics:
        timestamp = metric['time']
        if timestamp in thresholds:
            total_compared += 1
            crit_lower = thresholds[timestamp]['crit_lower']
            crit_upper = thresholds[timestamp]['crit_upper']
            metric_value = metric[metric_name]
            if (crit_lower > 0) and (metric_value < crit_lower):
                bad = True
#                print "(", i, ") LOW", crit_lower, metric_value
            elif (crit_upper > 0) and (metric_value > crit_upper):
#                print "(", i, ") HIGH", crit_upper, metric_value
                bad = True
            else:
                bad = False
            if bad:
#                print "BAD: ", timestamp, " = ", i
                bad_total += 1
            alerts.append((timestamp,bad))
        i += 1

#    print "TOTAL:", service_name, ":", key, ":", metric_name, " = ", i, " Compared: ", total_compared, "Min Points Required:", MIN_POINTS

    if (i < MIN_POINTS):
       panels_lacking_data = panels_lacking_data + 1
       print service_name, ':', key, ':', metric_name, i, MIN_POINTS, ": Total Alerts: Insufficient Data"
       return

    position = 0

    max = len(alerts)

    alerted = 0
    last_time_breached = False
    while position < max:
        breaches = 0
        for i in range(position, position + int(window)):
            if i >= max:
                break
#            print "    ", i, " = ", alerts[i][1]
            if alerts[i][1]:
                breaches += 1
        if breaches >= int(occurrences):
            if not last_time_breached:
                print service_name, metric_name, key, ": would have alerted", alerts[i]
                alerted += 1
#            else:
#                print "Already alerted"
            last_time_breached = True
        else:
            last_time_breached = False
        position += 1

    print service_name, ':', key, ':', metric_name, ": Total Alerts: ", alerted

    if (alerted == 0):
       ready_to_enable = ready_to_enable + 1



def get_formatted_timestamp(when):
    fmt = "%Y-%m-%d %H:%M:00"
    t = datetime.datetime.fromtimestamp(float(when))
    return t.strftime(fmt)


def format_percentage(a, b):
    x = (float(a) / float(b)) * 100
    y = int(x * 100)
    x = float(y) / 100
    return x

config = shputil.get_config()

when = int(time.time())

db_connection = get_db_connection()

service_config = ServiceConfiguration()

metric_db = config['influxdb_metric_policy'] + '.' + config['influxdb_metric_measure']
threshold_db = config['influxdb_threshold_policy'] + '.' + config['influxdb_threshold_measure']


for service in service_config.get_services():
    state = service.state
    service_name = service.name

#    if "SRW" not in service.name:
#        continue

    for panel in service.panels:
        total_panels += 1
        if service.is_validated() == False:
            panels_not_validated += 1
            print service_name, panel.panelKey, "Not validated"
            continue
        try:
            if ((str(panel.dynamic_alerting_enabled_high) == 'true') or (str(panel.dynamic_alerting_enabled_low) == 'true')):
               already_enabled = already_enabled + 1
               print "already done:", service_name, panel.panelKey, panel.dynamic_alerting_enabled
               continue

            metric = panel.metric_type
            key = panel.panelKey
            count_alerts(service_name, metric, key, when, panel)
        except Exception, e:
            print str(e)

db_connection.close()


print "\nTotal Panels:  ", total_panels
print "Not Validated: ", panels_not_validated
print "Lacking Data:  ", panels_lacking_data

total_panels_to_analyze = total_panels - (panels_not_validated + panels_lacking_data)
print "\nTotal Panels to Analyze:  ", total_panels_to_analyze

x = format_percentage(already_enabled, total_panels_to_analyze)
y = format_percentage(ready_to_enable, total_panels_to_analyze)

print "Alerting Already Enabled: ", already_enabled, '(', x, ')'
print "Ready to Enable Alerting:", ready_to_enable, '(', y, ')'
print "Grand Total:              ", x+y
