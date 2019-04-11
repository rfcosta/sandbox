import numpy as np
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri


class Predictor:

    def __init__(self, metric, historical_values, deviations):
        self.metric = metric
        self.historical_values = historical_values
        self.deviations = deviations
        self.time_series_columns = list()
        self.load_training_data()


    def load_training_data(self):
        for point_in_time in self.historical_values:
            self.time_series_columns.append(point_in_time[1])

        ##############################################
        ##############STL CLEANING####################
        ##############   Start    ####################

        pandas2ri.activate()

        ro.globalenv['r_time_series'] = np.array(self.time_series_columns)

        ro.r('library(forecast)')

        ro.r('library(zoo)')

        ro.r('r_time_series<-na.locf(r_time_series)')

        ro.r('r_time_series<-as.numeric(r_time_series)')

        # -----------------#

        ro.r('f1<-1440')

        # ro.r('y<-tsclean(r_time_series)')
        ro.r('y<-r_time_series')

        ro.r('y<-log(y+1)')

        ro.r('data.ts<-ts(as.numeric(y),start=1,frequency=f1)')

        ro.r('stlf_out<-stlf(data.ts,h=60,s.window="periodic")')

        ro.r('out2.ts<-ts((exp(stlf_out$mean)-1),start=1,frequency=f1)')

        ro.r('y_temp<-c(r_time_series,as.numeric(out2.ts))')

        ro.r('x<-(1:length(y_temp))')

        ro.r('y_temp_smoothed<-loess(y_temp ~ x,span=0.001)')

        ro.r('out2.ts<-tail(y_temp_smoothed$fitted,length(out2.ts))')

        ro.r('sd1<-sd((as.numeric(r_time_series)-head(y_temp_smoothed$fitted,length(y))))')

        # ro.r('print(paste("This is sd",sd1,sep=":"))')

        self.forecast = ro.r('as.numeric(out2.ts)')
        self.standard_dev = ro.r('as.numeric(sd1)')
        # -----------------#

        ro.r('rm(stlf_out,data.ts, f1, out2.ts, sd1, x, y, y_temp, y_temp_smoothed)')

        ro.r('gc()')

        ##############STL CLEANING####################
        ##############   End    ######################
        ##############################################


    def predict(self):
        lgbPreds = self.forecast

        sd = np.std(self.time_series_columns)
        lower_limit = lgbPreds - (self.deviations * sd)
        upper_limit = lgbPreds + (self.deviations * sd)

        lower_limit = [max(i, 0.0) for i in lower_limit]

        return (lower_limit, upper_limit)
