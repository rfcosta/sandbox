#!/bin/sh

# 8FFNanmso5KHxIb
sudo egrep -e 'password\s=\s\S+' /etc/grafana/grafana.ini  | head -1 | awk '{print $3}'
set -x
mysql -u masterUser -p -h rds-dev-us-east-1-shp.cjszqbbwgqsq.us-east-1.rds.amazonaws.com
set -


