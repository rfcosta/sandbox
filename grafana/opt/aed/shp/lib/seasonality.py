import numpy as np
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri

DAILY_AND_WEEKLY = [1440, 10080]
DAILY_ONLY = [1440]
DEFAULT = [15]


class Seasonality:

    def __init__(self, historical_values):
        is_daily = self.has_seasonality(historical_values, 1440)
        is_weekly = self.has_seasonality(historical_values, 10080)

        if is_weekly:
            self.seasons = DAILY_AND_WEEKLY
        elif is_daily:
            self.seasons = DAILY_ONLY
        else:
            self.seasons = DEFAULT

    def has_seasonality(self, historical_values, timespan):
        time_series_columns = list()

        for point_in_time in historical_values:
            time_series_columns.append(point_in_time[1])

        pandas2ri.activate()

        ro.globalenv['r_time_series'] = np.array(time_series_columns)
        ro.globalenv['r_timespan'] = timespan

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

                return(ANS)
                }

            ret = (seasonal_check(as.numeric(r_time_series),r_timespan))
       ''')

        return ro.r('as.logical(ret)')

    def get_seasons(self):
        return self.seasons
