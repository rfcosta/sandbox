#!/usr/bin/env bash

LOCAL_IP=$(hostname -I | sed -e 's/[[:space:]]*$//')

/usr/bin/influxd-ctl remove-meta -force -y -tcpAddr ${LOCAL_IP}:8089 ${LOCAL_IP}:8091
