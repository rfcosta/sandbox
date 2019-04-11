#!/bin/env python

# This program reads the Service feed from Service Now and updates the static thresholds in influxdb

import time
import os
import logging
from influxdb import InfluxDBClient

import sys
sys.path.append('/opt/aed/shp/lib')

from service_configuration import ServiceConfiguration

import shputil

State_Undefined         = 'undefined'
State_Staging_No_Alert  = 'staging-no-alerting'
State_Staging_Alert     = 'staging-alerting'
State_Staging_Validated = 'validated'

services = []

def write_thresholds_to_influx(client, ci, metric, panelKey, need_to_alert, warn_lower, warn_upper, crit_lower, crit_upper):
  json_body = [
    {
      "measurement": "thresholds",
      "tags": {
            "ci": ci,
            "type": "static",
            "metric": metric,
            "key": panelKey,
            "need_to_alert": need_to_alert
      },
      "fields": {
            metric + '_warn_lower': warn_lower,
            metric + '_warn_upper': warn_upper,
            metric + '_crit_lower': crit_lower,
            metric + '_crit_upper': crit_upper,
      }
    }
  ]
  logging.debug(json_body)
  client.write_points(json_body)

def process_json(client, service_config):

  for service in service_config.get_services():

    state = service.state
    panels = service.panels

    #===========================================================================
    #                       -----------Display State-------------------------
    #    STATES                ACTIVE                    INACTIVE
    # --------------------+-------------------------+-------------------------
    #  Undefined          |  Do Nothing             |  Do Nothing
    #  Staging (No Alert) |  Write / Alert Tag off  |  Write / Alert Tag off
    #  Staging (Alert)    |  Write / Alert Tag on   |  Write / Alert Tag off
    #  Validated          |  Write / Alert Tag on   |  Write / Alert Tag off
    #===========================================================================

    for panel in panels:
      metric_type = panel.metric_type
      panelKey = panel.panelKey
      thresholds = panel.thresholds
      display_state = panel.display_state
      alerting_enabled = panel.alerting_enabled

      need_to_write = state != State_Undefined
      need_to_alert = alerting_enabled == 'true' and display_state == 'Active' and state != State_Undefined and state != State_Staging_No_Alert

      warn_lower = thresholds.warn_lower
      warn_upper = thresholds.warn_upper
      crit_lower = thresholds.crit_lower
      crit_upper = thresholds.crit_upper

      if need_to_write:
        write_thresholds_to_influx(client, service.name, metric_type, panelKey, need_to_alert, float(warn_lower), float(warn_upper), float(crit_lower), float(crit_upper))

try:
    config = shputil.get_config()
    shputil.configure_logging(config["logging_configuration_file"])
    client = InfluxDBClient(host=config['influxdb_host'], port=int(config['influxdb_port']), database=config['influxdb_db'])
    service_config = ServiceConfiguration()
    process_json(client, service_config)
except Exception, e:
    logging.error("Failure: Error processing service configurations", exc_info=True)
