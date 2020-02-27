import json
import sys

sys.path.append('/opt/aed/shp/lib')

import shputil
import os
from service import Service
from topLevelService import TopLevelService


##################################################################
#
# this will parse the service configuration file from Service Now.
#
# Example Usage:
#
# from service_configuration import ServiceConfiguration
# service_config = ServiceConfiguration()
#
# for service in service_config.get_services():
#    state = service.state
#    panels = service.panels
#
#    for panel in panels:
#       metric_type = panel.metric_type
#       display_state = panel.display_state
#       alerting_enabled = panel.alerting_enabled
#       dynamic_alerting_enabled = panel.dynamic_alerting_enabled
#       thresholds = panel.thresholds
#
#       warn_lower = thresholds.warn_lower
#       warn_upper = thresholds.warn_upper
#       crit_lower = thresholds.crit_lower
#       crit_upper = thresholds.crit_upper
#
# You can also pull specific services by name
#
# service = service_config.get_service(my_service_name):
#
##################################################################


class ServiceConfiguration:

    def __init__(self):
        self.config = shputil.get_config()
        self.config_file = self.config['service_configuration_file']

        self.services = {}
        self.topLevelServices = {}

        if not os.path.exists(self.config_file):
            os.system("/opt/aed/shp/bin/download_service_configurations.py")

        with open(self.config_file, 'r') as fp:
            self.results = json.load(fp)

        if 'global' in self.results['result'] and 'version' in self.results['result']['global']:
            self.version = self.results['result']['global']['version']
        else:
            self.version = "undefined"

        # temporary until we figure out the SNOW/SHP mismatched versions problem
        if 'global' in self.results['result'] and 'use_configured_panelIDs' in self.results['result']['global']:
            self.use_configured_panelIDs = self.results['result']['global']['use_configured_panelIDs']
        else:
            self.use_configured_panelIDs = "false"

        if 'global' in self.results['result'] and 'global_dynamic_alerting_deviations_adjustment' in \
                self.results['result']['global']:
            self.dynamic_alerting_deviations_adjustment = self.results['result']['global'][
                'global_dynamic_alerting_deviations_adjustment']
        else:
            self.dynamic_alerting_deviations_adjustment = "0"

        self.load_services(self.results['result']['services'])
        self.load_top_level_services(self.results['result']['topLevelServices'])

    def load_top_level_services(self, top_level_services):
        for topLevelServiceObj in top_level_services:
            top_level_service = TopLevelService(topLevelServiceObj)
            self.topLevelServices[top_level_service] = top_level_service

    def get_top_level_services(self):
        return self.topLevelServices

    def load_services(self, services):
        for service in services:
            service = Service(service, services[service], self.use_configured_panelIDs)
            self.services[service] = service

    def get_services(self):
        return self.services

    def get_service(self, service_name):
        for service in self.services:
            if service.name == service_name:
                return service
        raise KeyError("Unable to find service: {0}".format(service_name))

    def __str__(self):
        s = 'Snow Application Version: ' + self.version + '\n\n'
        s += 'Use configured panel ID: ' + self.use_configured_panelIDs + '\n\n'
        for service in self.services:
            s = s + str(self.services[service]) + '\n'
        for topLevelService in self.topLevelServices:
            s = s + str(topLevelService) + '\n'
        return s
