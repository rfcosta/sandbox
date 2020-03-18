#!/bin/sh 

cd $HOME/_github/influxdata/grafana/opt/aed/shp

diff -rd --brief . ~/_shp/servicehealthportal/scripts/aed/shp/ |  awk '$(NF) == "differ" {printf "cp -v %s %s\n",  $(NF-1), $(NF-3)}'

