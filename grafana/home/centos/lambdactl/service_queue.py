
import sys
import os
import json
import copy
import time
import datetime
import re


PYTHON = sys.version
AWS = AwsUtil(__name__)
loggger = AWS.loggger
AWSVARS = AwsVars(AWS)


_XINTERVAL = re.compile("(\d+)([smhdw]*)")
_UNITS = dict(s=1
              , m=60
              , h=60 * 60
              , d=60 * 60 * 24
              , w=60 * 60 * 24 * 7
              )


class ServiceQueue():


    def __init__(self, ServiceConfiguration=dict(result=dict()), AwsVars=dict(), DataSources=["prometheus", "viz", "zabbix"]):
        self.ServiceConfiguration = ServiceConfiguration
        self.AwsVard = AwsVars
        self.DataSources = DataSources

        self.loadConfig()

        pass



    # Utility functions
    # =================

    def epoch2date(epoch):
        return datetime.datetime.fromtimestamp(float(epoch))

    def epochMinute(epoch):
        return int(epoch) // 60 * 60

    def nowMinute():
        pass

    def fmtTimestamp(epoch):
        return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(epoch))

    def parsePeriod(pstr):
        if pstr.isdigit():
            return int(pstr)

        number, unit = [60, 's']
        tokens = _XINTERVAL.match(pstr)
        if tokens:
            number, unit = tokens.groups()
            if number:
                number = int(number)
            if not unit:
                unit = 's'
            secondsInUnit = _UNITS.get(unit, 1)
        else:
            number = 60
            secondsInUnit = 1
        pass

        intervalSeconds = number * secondsInUnit

        loggger.debug("Interval %s, number %s, secondsInUnit %d, result: %d"
                      % (pstr, str(number), secondsInUnit, intervalSeconds)
                      )

        return intervalSeconds

    def loadConfig(self):
        servicesObject = self.ServiceConfiguration['result'].get('services', {})
        self.numberOfServices = servicesObject.keys().__len__()

        if self.numberOfServices > 0:
            services = [(sky, servicesObject[sky]) for sky in servicesObject.keys()]

            # Create a service map dictionary grouping all by source, ci
            self.service_map = dict()
            last_updated = self.ServiceConfiguration["result"]["last_updated"]
            _global = copy.deepcopy(self.ServiceConfiguration['result']["global"])
            _topLevelServices = [copy.deepcopy(x) for x in self.ServiceConfiguration["result"]["topLevelServices"]]
            _svc_property_names = ["state", "knowledge_article", "report_grouping", "service_config_sys_id", "uid"]

            for (ci, svc) in services:
                # loggger.debug("SVC ==> " + json.dumps(svc, indent=4))
                for (source, key, type) in [(svc['panels'][pky]['data_source'], pky, svc['panels'][pky]['metric_type'])
                                            for pky in svc['panels'].keys()]:
                    if source not in self.DataSources:
                        continue

                    loggger.debug("source: {0:16}, type: {3:20}, key: {2:50}, ci: {1} ".format(source, ci, key, type))

                    self.service_map.setdefault(source, {})
                    self.service_map[source].setdefault(ci, dict(config=dict(),
                                                            map=dict(types=[], keys=[], ci=ci, source=source)))
                    # service_map[source][ci].setdefault("map", dict(types=[], keys=[], ci=ci, source=source))
                    if type not in self.service_map[source][ci]["map"]["types"]:
                        self.service_map[source][ci]["map"]["types"].append(type)
                    self.service_map[source][ci]["map"]["keys"].append(key)

                    # From big configuration data, create a small config for this particular source
                    self.service_map[source][ci]["config"].setdefault \
                        ("result",
                             { "global": _global,
                               "services": {},
                               "topLevelServices": _topLevelServices,
                               "last_updated": last_updated
                             }
                         )
                    _empty_service = {"panels": {}}
                    for p in _svc_property_names:
                        _empty_service[p] = svc[p]

                    self.service_map[source][ci]["config"]["result"]["services"].setdefault(ci, _empty_service)
                    # service_map[source]["config"]["result"]["services"][ci]["panels"].setdefault(key, copy.deepcopy(servicesObject[ci]["panels"][key]))
                    _panel = copy.deepcopy(svc["panels"][key])
                    self.service_map[source][ci]["config"]["result"]["services"][ci]["panels"].setdefault(key, _panel)

                    pass
                pass
            pass
            # loggger.debug(json.dumps(service_map, indent=4))
            # print(json.dumps(service_map))

        pass