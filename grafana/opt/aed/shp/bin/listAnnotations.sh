#!/bin/sh

set -x

dashboardId=${1:-177}

orgId=1
user=admin
pswd=IamApass01
instance='servicehealth-dev.sabre.com'
instance='localhost'
port=443
port=3000
orgId=2
limit=100

URL="http://${user}:${pswd}@${instance}:${port}/api/annotations/?orgId=${orgId}&limit=${limit}&dashboardId=${dashboardId}&type=annotation"


if [ ! "x$dashboardId" = "x" ] ; then
    curl "${URL}" \
    --request GET \
    --header "Accept:application/json" \
    --header "content-type:application/json" \
    --header "X-Grafana-Org-Id:${orgId}" \
    --user $user:$pswd
fi

set -


