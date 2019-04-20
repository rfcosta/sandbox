import json
import sys

sys.path.append('/opt/aed/shp/lib')
sys.path.append('/opt/aed/shp/lib/grafana')

import shputil
import os
from service_configuration import ServiceConfiguration
from helper import Helper

def listGLBL(svconfig):
    if 'global' in svconfig.results['result']:
        _globals = svconfig.results['result']['global']
        _version                    = _globals.get('version', None)
        _snow_instance              = _globals.get('servicenow_instance', '')
        _use_configured_panelIDs    = _globals.get("use_configured_panelIDs", False)
        _use_appd_configuration     = _globals.get("use_appd_configuration",  False)
        _create_change_requests     = _globals.get("create_change_requests",     30)
        _global_stale_data_minutes  = _globals.get("global_stale_data_minutes",  30)

        print("_version                   " + str(_version                   ))
        print("_snow_instance             " + str(_snow_instance             ))
        print("_use_configured_panelIDs   " + str(_use_configured_panelIDs   ))
        print("_use_appd_configuration    " + str(_use_appd_configuration    ))
        print("_create_change_requests    " + str(_create_change_requests    ))
        print("_global_stale_data_minutes " + str(_global_stale_data_minutes ))

        return True
    else:
        return False

svccfg = ServiceConfiguration()
result = listGLBL(svccfg)
