#!/bin/env python

import time
import sys
import json
import os
from influxdb import InfluxDBClient

sys.path.append('/opt/aed/shp/lib')

from service_configuration import ServiceConfiguration

import shputil

def print_report(service, metric, key):
  query = 'SELECT ' + metric + ' FROM ' + db + "." + policy + "." + measure + ' WHERE ci=\'' + service + '\'' + ' AND "key"=\'' + key  + '\'' + ' AND "type"=\'' + metric + '\''
  print "QUERY: " + query
  rs = client.query(query)

  service = service.replace('/','-')
  service = service.replace(' ','-')
  service = service.replace(':','-')
  fname = "FILES/" + service + '^' + key + '^' + metric + '.csv'
  f= open(fname,"w+")
  f.write( "time,service," + key + '\n')
  for item in rs.get_points():
    value = item[metric]
    if value is not None:
      f.write( item['time'] + ',' + ci + ',' + str(value) + '\n'  )
  f.close()

# mainline

os.system("rm FILES/*")
config = shputil.get_config()

client = InfluxDBClient(host=config['influxdb_host'], port=int(config['influxdb_port']), database=config['influxdb_db'])

db = config['influxdb_db']
policy = config['influxdb_metric_policy']
measure = config['influxdb_metric_measure']

service_config = ServiceConfiguration()

for service in service_config.get_services():
   if  service.state == 'undefined':
      continue
#   if "ATSE" not in service.name:
#      continue
   ci = service.name
   panels = service.panels
   for panel in panels:
     print str(panel)
     key = panel.panelKey
     metric = panel.metric_type
     if key:
       print "KEY: " + key + " SERVICE: " + ci
       print_report(ci, metric, key)

client.close()

