#!/bin/sh

set -x

dashboardId=${1:-216}

orgId=1
user=admin
pswd=IamApass01
instance='servicehealth-dev.sabre.com'
port=443
orgId=2
limit=100
type=alert

instance='localhost'
port=3000
type=annotation
regionId = 0


URL="http://${user}:${pswd}@${instance}:${port}/api/annotations/?orgId=${orgId}&limit=${limit}&dashboardId=${dashboardId}&regionId=${regionId}" # &type=${type}"


if [ ! "x$dashboardId" = "x" ] ; then
    curl "${URL}" \
    --request GET \
    --header "Accept:application/json" \
    --header "content-type:application/json" \
    --header "X-Grafana-Org-Id:${orgId}" \
    --user $user:$pswd | python -m json.tool > listAnnotations.json
fi

set -


