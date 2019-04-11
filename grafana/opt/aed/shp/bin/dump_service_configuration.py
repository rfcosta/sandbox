#!/bin/env python

import sys
sys.path.append('/opt/aed/shp/lib')

# Simple application to dump the service configuration in a readable format

from service_configuration import ServiceConfiguration

service_config = ServiceConfiguration()

print str(service_config)
