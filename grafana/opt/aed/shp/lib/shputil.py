import os
import json
import logging
import logging.config
from requests.auth import HTTPBasicAuth

config_file = "/opt/aed/shp/conf/alerting-config.json"

def get_config():
    try:
        config = json.load(open(config_file))
        return config
    except:
        print "Error reading config file " + config_file
        exit(1)


def get_proxy():
    return { "https" : "http://proxy.us-west-2.dev.int:3128" }


def get_appdynamics_base_api_url():
    return "https://" + config["appdynamics_instance"] + ".saas.appdynamics.com/controller/rest/"


def get_appdynamics_auth():
    return config["appdynamics_user"] + '@' + config["appdynamics_domain"], config["appdynamics_pass"]


def get_servicenow_base_api_url():
    return "https://" + config["servicenow_user"] + ":" + config["servicenow_pass"] + "@" + config["servicenow_instance"] + ".service-now.com/api/now/table/"


def get_grafana_base_api_url():
    return "http://" + config["grafana_user"] + ":" + config["grafana_pass"] + "@" + config["grafana_host"] + "/api/"


def get_grafana_credentials():
    return HTTPBasicAuth(config['grafana_user'], config['grafana_pass'])


def get_influxdb_base_url():
    return config["influxdb_url"]


def configure_logging(logFile):
    logging.config.fileConfig(logFile)

config = get_config()
