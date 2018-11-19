#!/bin/sh

docker ps -a | awk -v WITDH=145 '{print substr($0,1,WITDH)}'



# CONTAINER ID        IMAGE                      COMMAND                  CREATED              STATUS                      PORTS                                                                    NAMES
# 3d34c7798eab        grafana                    "/run.sh"                About a minute ago   Up About a minute           0.0.0.0:3000->3000/tcp                                                   influxdata_grafana_1
# 0420a768e8fa        chrono_config              "/entrypoint.sh chro…"   About a minute ago   Up About a minute           0.0.0.0:8888->8888/tcp                                                   influxdata_chronograf_1
# 3f36c0d32054        kapacitor                  "/entrypoint.sh kapa…"   About a minute ago   Up About a minute           0.0.0.0:9092->9092/tcp                                                   influxdata_kapacitor_1
# 3e777738e16d        telegraf                   "/entrypoint.sh tele…"   About a minute ago   Up About a minute           8092/udp, 8125/udp, 8094/tcp                                             influxdata_telegraf_1
# e45c53692801        influxdb                   "/entrypoint.sh infl…"   About a minute ago   Up About a minute           0.0.0.0:8082->8082/tcp, 0.0.0.0:8086->8086/tcp, 0.0.0.0:8089->8089/tcp   influxdata_influxdb_1
# b54274eea091        influxdata_documentation   "/documentation/docu…"   About a minute ago   Up About a minute           0.0.0.0:3010->3000/tcp                                                   influxdata_documentation_1
# be5bc112767f        hello-world                "/hello"                 5 weeks ago          Exited (0) 5 weeks ago                                                                               flamboyant_jang
# 64af8e775944        centos:regi                "/bin/bash"              7 months ago         Exited (127) 7 months ago                                                                            quirky_mcnulty