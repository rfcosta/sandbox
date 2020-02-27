import json
import logging.config
import os
from requests.auth import HTTPBasicAuth

config_file = "/opt/aed/shp/conf/alerting-config.json"


def check_logged_in_user(expected_user):
    actual_user = os.getenv('LOGNAME')
    if actual_user != expected_user:
        print("This script needs to run as {0}.".format(expected_user))
        exit(-1)


def get_config():
    try:
        return json.load(open(config_file))
    except:
        print("Error reading config file {0}".format(config_file))
        exit(1)


def get_appdynamics_base_api_url():
    return "https://" + config["appdynamics_instance"] + ".saas.appdynamics.com/controller/rest/"


def get_appdynamics_auth():
    return config["appdynamics_user"] + '@' + config["appdynamics_domain"], config["appdynamics_pass"]


def get_servicenow_base_api_url():
    return "https://" + config["servicenow_user"] + ":" + config["servicenow_pass"] + "@" + \
           config["servicenow_instance"] + ".service-now.com/api/now/table/"


def get_grafana_base_api_url():
    return "http://" + config["grafana_user"] + ":" + config["grafana_pass"] + "@" + config["grafana_host"] + "/api/"


def get_grafana_credentials():
    return HTTPBasicAuth(config['grafana_user'], config['grafana_pass'])


def get_influxdb_base_url():
    return config["influxdb_url"]


def configure_logging(logging_config_file):
    if 'json' in logging_config_file:
        configure_logging_using_json(logging_config_file)
    else:
        configure_logging_using_ini(logging_config_file)


def configure_logging_using_ini(logging_config_file):
    logging.config.fileConfig(logging_config_file)


def configure_logging_using_json(logging_config_file):
    with open(logging_config_file, "r") as fd:
        config_dict = json.load(fd)
    logging.config.dictConfig(config_dict["logging"])


def get_logger(logger_name):
    configure_logging(config["logging_configuration_file"])
    return logging.getLogger(logger_name)


config = get_config()
