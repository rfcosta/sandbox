import json
import logging
import sys

import requests

sys.path.append('/opt/aed/shp/lib')
sys.path.append('/opt/aed/shp/lib/grafana')

import shputil
from service_configuration import ServiceConfiguration
from folders import Folders
from dashboards import Dashboards
from helper import Helper

columns = 3

folders = {}
dashboards = {}

used_folders = {}
used_dashboards = {}

config = shputil.get_config()
shputil.configure_logging(config["logging_configuration_file"])

main_org_id = 1
staging_org_id = 2
aggregate_org_id = 3

service_config = ServiceConfiguration()

print("*** END TEST ***")
