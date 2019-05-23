#!/bin/sh

set -x

region=${1:-373845}

orgId=1
user=admin
pswd=IamApass01
instance='servicehealth-dev.sabre.com'
instance='localhost'
port=443
port=3000
orgId=2

URL="http://${user}:${pswd}@${instance}:${port}/api/annotations/region/${region}?orgId=${orgId}"

if [ ! "x$region" = "x" ] ; then
    curl "${URL}" \
    --request DELETE \
    --header "Accept:application/json" \
    --header "content-type:application/json" \
    --header "X-Grafana-Org-Id:${orgId}" \
    --user $user:$pswd
fi

set -

