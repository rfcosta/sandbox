import os
import sys
import time



class AwsVars(object):


    def __init__(self, awsutil):

        self.nowLocal           = time.localtime()
        self.nowGmt             = time.gmtime()
        self.AWS = awsutil

        self.queueUrl           = os.environ.get('queueUrl',           "https://sqs.us-west-2.amazonaws.com/816835746341/shp-dev-queue-input-0000")
        self.snowFileName       = os.environ.get('snowFileName',       "cache/ServiceConfiguration.json")
        self.globalPrefix       = os.environ.get('globalPrefix',       "servicehealth-dev")
        self.queueUrl           = os.environ.get('queueUrl',           "https://sqs.us-west-2.amazonaws.com/816835746341/shp-dev-queue-input-0000")
        self.snowUserName       = os.environ.get('snowUserName',       "WS_EVENT_NONP_HEALTHPORTAL")
        self.snowPassHash       = os.environ.get('snowPassHash',       "AQICAHjlHPOLgWSl53szICkKRXxi+8RMTEXhaolIxBQ9WFk1OQGSGVMQg7hJAE2neayg/Mw9AAAAaDBmBgkqhkiG9w0BBwagWTBXAgEAMFIGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQM+sBj2p9sb6tomR9OAgEQgCVQVM65g3LiQmvIVZHEKtNxPMbHnEZLNW86o9X8yRPzt2inshiF")
        self.s3Bucket_name      = os.environ.get('s3Bucket_name',      "s3-dev-us-west-2-shp-data-0000")
        self.influxHost         = os.environ.get('influxHost',         "influx-elb-0000.us-west-2.teo.dev.ascint.sabrecirrus.com")
        self.influxPort         = os.environ.get('influxPort',         "8086")
        self.influxUrl          = os.environ.get('influxUrl',          "http://influx-elb-0000.us-west-2.teo.dev.ascint.sabrecirrus.com:8086")
        self.proxyUrl           = os.environ.get('proxyUrl',           "http://proxy.us-west-2.teo.dev.ascint.sabrecirrus.com:3128")
        self.InfluxQryTimeFrame = os.environ.get('InfluxQryTimeFrame', "24h")


    def dumpEnvironmentVars(self):

        _loggger = self.AWS.loggger
        _loggger.debug(' Environment vars:')
        for key in self.__dict__.keys():
            _loggger.debug(" {0:24} {1}".format(key + ":", self.__dict__[key]))

        return
