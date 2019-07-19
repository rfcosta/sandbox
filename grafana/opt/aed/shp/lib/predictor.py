import numpy as np
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri


class Predictor:

    def __init__(self, metric, historical_values, seasonal_periods, deviations, minutes_to_predict):
        self.metric = metric
        self.historical_values = historical_values
        print "Seasonal Periods: ", seasonal_periods
        self.seasonal_periods = seasonal_periods
        self.deviations = deviations
        self.minutes_to_predict = minutes_to_predict
        self.time_series_columns = list()
        self.load_training_data()


    def load_training_data(self):
        for point_in_time in self.historical_values:
            self.time_series_columns.append(point_in_time[1])

        pandas2ri.activate()

        ro.globalenv['r_time_series'] = np.array(self.time_series_columns)
        ro.globalenv['periods'] = self.seasonal_periods
        ro.globalenv['minutes_to_predict'] = self.minutes_to_predict

        ro.r('periods<-as.numeric(periods)')

        ro.r('library(forecast)')
        ro.r('library(zoo)')

        ro.r('r_time_series<-na.locf(r_time_series)')
        ro.r('r_time_series<-as.numeric(r_time_series)')

        ro.r('''preprocess_jumps <- function(input, periods=c(1440, 10080), hours=8)
          ###-------------------------------------------------------------------------###
          ### The function preprocess_jumps deals with the abrupt changes at the
          ### beginning of the time series. It removes effects of outliers at the
          ### in the most recent data points of the time series. It decomposes the
          ### time series and replaces the trend component with a rolling median.
          ### hours: specificies how many past hours should be used in the calculation
          ### periods: specify the seasonality to use when doing the decomposition
          ### input: specifies the time series data to be used.
          ###-------------------------------------------------------------------------###
          {
              l <- length(as.numeric(input))
              input.msts <-msts(input, start=1, seasonal.periods = periods)
              input_decom <-mstl(input.msts, s.window = 'periodic',robust=TRUE)
              data_mod <- as.numeric(input_decom[, 2])
              temp <- data_mod
              data_mod<-rollmedian(temp,(60*hours+1),align = 'right')
              temp[(60*hours+1):l]<-data_mod
              for (i in (3:(2 + length(periods)))){temp <- temp +as.numeric(input_decom[, i])}
              final <- msts(temp, start=1, seasonal.periods = periods)
              return (final)
          }
          time_series_original <- r_time_series
          r_time_series <- preprocess_jumps(r_time_series, periods=c(1440,10080), hours=8)
          r_time_series <- as.numeric(r_time_series)
        ''')

        ro.r('''
          ###-------------------------------------------------------------------------###
          ### Log transform data to ensure that we always have positive predictions.
          ### In the case of abrupt drops in a metric the prediction may become negative
          ### which would be unacceptable and we take log transformation to prevent that.
          ### We add a constant of 1 to deal with cases where the metric is 0, since log 0
          ### is undefined.
          ###-------------------------------------------------------------------------###
          y<-r_time_series
          y<-log(y+1)
          ###-------------------------------------------------------------------------###
          ### Create time serie object with the seasonalities used.
          ###-------------------------------------------------------------------------###
          data.ts<-msts(as.numeric(y),start=1,seasonal.periods=periods)
          ###-------------------------------------------------------------------------###
          ### Do decomposition based prediction for the next 60 minutes.
          ###-------------------------------------------------------------------------###
          stlf_out<-stlf(data.ts,h=minutes_to_predict,s.window="periodic",robust=TRUE)
          ###-------------------------------------------------------------------------###
          ###  Transform the predictions back to the original form by exponentiating and
          ###  subtracting 1. The convert to multiple seasonality time series object.
          ###-------------------------------------------------------------------------###
          out2.ts<-msts((exp(stlf_out$mean)-1),start=1,seasonal.periods=periods)
          ###-------------------------------------------------------------------------###
          ### The predictions are very jagged and rough and represent the jagged nature of
          ### the data. So we apply loess smoothing to the final prediction. But in order 
          ### do so we recombine to the original time series first. Then we do loess
          ### smoothing over the entire data set combined with predictions. The we extract
          ### only the smoothes version of the predictions.
          ###-------------------------------------------------------------------------###
          y_temp<-c(r_time_series,as.numeric(out2.ts))
          x<-(1:length(y_temp))
          y_temp_smoothed<-loess(y_temp ~ x,span=0.001)
          out2.ts<-tail(y_temp_smoothed$fitted,length(out2.ts))
          sd1<-sd((as.numeric(r_time_series)-head(y_temp_smoothed$fitted,length(y))))
        ''')

        ro.r('''       
          ###-------------------------------------------------------------------------###
          ### Calculate an "standard deviation (sd)" type number to use for upper and lower 
          ### bounds. Using a regular sd of residuals were not appropriate and gave bands 
          ### that we too low so we create a function called variance that looks at 
          ### seasonal random walk walk residuals for a lead time of 5040 minutes (3.5 days)
          ###-------------------------------------------------------------------------###
          variance<-function(y) {
            lead<-5040
            l<-length(y)
            recent<-y[(lead+1):(l)]
            past<-y[(1):(l-lead)]       
            var1<-sqrt(sum((abs(y[(lead+1):(l)]-y[(1):(l-lead)])^2))/l)        
            return(var1)        
          }

          sd1<-variance(as.numeric(time_series_original))   
          sd2<-sd(as.numeric(time_series_original))
        ''')

        self.standard_dev = ro.r('as.numeric(sd1)')
        self.forecast = ro.r('as.numeric(out2.ts)')

        ro.r('rm(stlf_out,data.ts, f1, out2.ts, sd1, x, y, y_temp, y_temp_smoothed)')
        ro.r('gc()')


    def predict(self):
        lgbPreds = self.forecast

        lower_limit = lgbPreds - (self.deviations * self.standard_dev)
        upper_limit = lgbPreds + (self.deviations * self.standard_dev)

        lower_limit = [max(i, 0.0) for i in lower_limit]

        return (lower_limit, upper_limit)


