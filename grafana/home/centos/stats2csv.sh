#!/usr/bin/env bash

file=/Users/regi/_github/influxdata/grafana/home/centos/stats.txt

awk '\

function durationInSeconds(time) {
    split(time, T, "m");
    tminutes = T[1];

    split(T[2], S, "s");
    tseconds = S[1];

    totalseconds = tminutes * 60 + tseconds;
    return totalseconds;
}

substr($1,length($1),1) == "m"  {
    timeframe = $1;
    minutes   = substr($1,1,length($1) - 1);
}
substr($1,length($1),1) == "h"  {
    timeframe = $1;
    minutes   = substr($1,1,length($1) - 1) * 60;
}
substr($1,length($1),1) == "d"  {
    timeframe = $1;
    minutes   = substr($1,1,length($1) - 1) * 60 * 24;
}
$1 == "real" {
    real = $2;
}
$1 == "user" {
    user = $2;
}
BEGIN {
    printf "%5s, %6s, %10s, %10s, %10s, %10s, %10s, %10s\n", "min", "frame", "real", "user", "sys", "sreal", "suser", "ssys"
}
$1 == "sys" {
    sys = $2;
    printf "%5s, %6s, %10s, %10s, %10s, %10s, %10s, %10s\n", minutes, timeframe, real, user, sys, durationInSeconds(real), durationInSeconds(user), durationInSeconds(sys) ;
}

' \
$file
