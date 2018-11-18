#!/bin/sh

# ....+....1....+....2....+....3....+....4....+....5....+....6....+....7....+....8....+....9....+...10....+...11....+...12....+...13....+...14....+
# CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS                      PORTS               NAMES
# be5bc112767f        hello-world         "/hello"            5 weeks ago         Exited (0) 5 weeks ago                          flamboyant_jang
# 64af8e775944        centos:regi         "/bin/bash"         7 months ago        Exited (127) 7 months ago                       quirky_mcnulty

# 1-13                21-40               41-60               61-80               81-108                      109-128             129-145

ID="1-13"
IMAGE="21-40"
COMMAND="41-60"
CREATED="61-80"
STATUS="81-108"
PORTS="109-128"
NAMES="129-145"

docker ps -a | cut -c $ID,$IMAGE,$COMMAND,$STATUS,$NAMES -



