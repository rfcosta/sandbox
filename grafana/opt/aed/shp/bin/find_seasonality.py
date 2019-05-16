#!/bin/env python

import sys

from influxdb import InfluxDBClient

sys.path.append('/opt/aed/shp/lib')

from service_configuration import ServiceConfiguration
import shputil

import numpy as np
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri

THREE_WEEKS = 60 * 24 * 21


def get_db_connection():
    influx_host = config['influxdb_host']
    influx_port = config['influxdb_port']
    influx_db = config['influxdb_db']
    return InfluxDBClient(host=influx_host, port=influx_port, database=influx_db)


def find_best_season(historical_values):
    time_series_columns = list()

    for point_in_time in historical_values:
        time_series_columns.append(point_in_time[1])

    pandas2ri.activate()

    ro.globalenv['r_time_series'] = np.array(time_series_columns)
    ro.r('library(forecast)')
    ro.r('library(zoo)')
    ro.r('library(plyr)')
    ro.r('as.Date <- base::as.Date')
    ro.r('as.Date.numeric <- base::as.Date.numeric')
    ro.r('''
        stlf1<-function (y, h = frequency(x) * 2, s.window = 13, t.window = NULL,
                 robust = FALSE, lambda = NULL, biasadj = FALSE, x = y, ...)
        {
            seriesname <- deparse(substitute(y))
            if (NCOL(x) > 1L) {
                stop("y must be a univariate time series")
            }
            else {
                if (!is.null(ncol(x))) {
                    if (ncol(x) == 1L) {
                       x <- x[, 1L]
                    }
                }
            }
            tspx <- tsp(x)
            if (is.null(tspx)) {
                stop("y is not a seasonal ts object")
            }
            if (!is.null(lambda)) {
                x <- BoxCox(x, lambda)
                lambda <- attr(x, "lambda")
            }
            fit <- mstl(x, s.window = s.window, t.window = t.window, robust = robust)
            fcast <- forecast(fit, h = h, lambda = lambda, biasadj = biasadj, ...)
            fcast$series <- seriesname
            return(fcast)
        }

        seasonal_check<-function(y,season){
            require(forecast)
            require(plyr)
            l<-length(as.numeric(y))
            n0<-max(season,1000)
            train<-y[1:(l-n0)]
            test<-y[(l-n0+1):l]

            mod_season<-stlf(train.ts<-ts(train,start=1,frequency =season),s.window='periodic',h=n0)
            ERROR_season<-abs(mod_season$mean-test)

            mod_noseason<-stlf1(train.ts<-ts(train,start=1,frequency =1),s.window ='periodic',h=n0)

            ERROR_noseason<-abs(mod_noseason$mean-test)

            check<-NULL
            check<-(as.numeric(ERROR_season)<as.numeric(ERROR_noseason))
            ANS<-NULL
            check_true<-subset(count(check),x==TRUE)$freq
            check_false<-subset(count(check),x==FALSE)$freq

            if ( (length(check_true)==0 ) & (length(check_false)==0)) { stop("Something Went Wrong!") }

            if( length(check_true)==0){
                if(length(check_false)!=0 & (check_false/(length(check)))==1){
                    ANS<-FALSE
                } else {
                    stop("Not Clear if Seasonality Present!")}
                }

            if( length(check_true)!=0){
                if (check_true/(length(check))>0.75 ){
                    ANS<-TRUE
                } else {
                    ANS<- FALSE
                }
            }

            #print(prop.table(table(check)))
            return(ANS)
            }

        ret = (seasonal_check(as.numeric(r_time_series),10080))
   ''')

    return ro.r('as.logical(ret)')

def process_metric(service, panel):
    service_name = service.name
    metric = panel.metric_type
    key = panel.panelKey
#    print service_name, " - ", metric
    formatter = "SELECT time, mean({0}) AS {0} FROM {1} WHERE \"key\"='{2}' AND ci='{3}' GROUP BY time(1m) fill(previous)"
    query = formatter.format(metric, metric_db, key, service_name)
    rs = db_connection.query(query)

    historical_data = []

    for item in rs.items():
        for point in item[1]:
            if None == point[metric]:
                continue
            time = point['time']
            value = point[metric]
            single_tuple = (time, value)
            historical_data.append(single_tuple)

    if len(historical_data) < THREE_WEEKS:
#        print service_name, "-", metric, "- Not enough data"
        return

    x = find_best_season(historical_data)[0]
    print service_name, "-", key, "-", metric, "-", x


config = shputil.get_config()

db_connection = get_db_connection()

service_config = ServiceConfiguration()

metric_db = config['influxdb_metric_policy'] + '.' + config['influxdb_metric_measure']
threshold_db = config['influxdb_threshold_policy'] + '.' + config['influxdb_threshold_measure']

for service in service_config.get_services():
    state = service.state
    service_name = service.name
    for panel in service.panels:
        try:
            process_metric(service, panel)
        except Exception as e:
            print e
#    break
