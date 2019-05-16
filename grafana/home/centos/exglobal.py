import json
import sys

sys.path.append('/opt/aed/shp/lib')
sys.path.append('/opt/aed/shp/lib/grafana')
# sys.path.append('../../opt/aed/shp/lib')
# sys.path.append('../../opt/aed/shp/lib/grafana')

import shputil
import os
from service_configuration import ServiceConfiguration
from helper import Helper

def getGLBL(svconfig):
    if 'global' in svconfig.results['result']:
        _globals = svconfig.results['result']['global']
        _version                    = _globals.get('version', None)
        _snow_instance              = _globals.get('servicenow_instance', '')
        _use_configured_panelIDs    = True if (_globals.get("use_configured_panelIDs", "false") == "true") else False
        _use_appd_configuration     = True if (_globals.get("use_appd_configuration",  "false") == "true") else False
        _create_change_requests     = _globals.get("create_change_requests",     30)
        _global_stale_data_minutes  = _globals.get("global_stale_data_minutes",  30)

        return dict(
            version                     = _version,
            snow_instance               = _snow_instance,
            use_configured_panelIDs     = _use_configured_panelIDs,
            use_appd_configuration      = _use_appd_configuration,
            create_change_requests      = _create_change_requests,
            global_stale_data_minutes   = _global_stale_data_minutes
        )

def printGLBL(_GLBL):
    for _name, _value in _GLBL.items():
        print( "%-30s %s" % (_name, str(_value)) )

    return True

svccfg = ServiceConfiguration()
_GLBL  = getGLBL(svccfg)
result = printGLBL(_GLBL)

print(result)
print(json.dumps(_GLBL, indent=4))


