import os
import sys
import time

from logger_util import LoggerUtil

LOG = LoggerUtil(__name__)
loggger = LOG.loggger

class AwsVars(object):


    def __init__(self):

        self.nowLocal           = time.localtime()
        self.nowGmt             = time.gmtime()

        self.queueUrl           = os.environ.get('queueUrl',           "https://sqs.us-west-2.amazonaws.com/816835746341/shp-dev-queue-input-0000")
        self.snowFileName       = os.environ.get('snowFileName',       "cache/ServiceConfiguration.json")
        self.queueUrl           = os.environ.get('queueUrl',           "https://sqs.us-west-2.amazonaws.com/816835746341/shp-dev-queue-input-0000")
        self.s3BucketName       = os.environ.get('s3BucketName',       "s3-dev-us-west-2-shp-data-0000")
        self.influxHost         = os.environ.get('influxHost',         "influx-elb-0000.us-west-2.teo.dev.ascint.sabrecirrus.com")
        self.influxPort         = os.environ.get('influxPort',         "8086")
        self.influxUrl          = os.environ.get('influxUrl',          "http://influx-elb-0000.us-west-2.teo.dev.ascint.sabrecirrus.com:8086")
        self.proxyUrl           = os.environ.get('proxyUrl',           "http://proxy.us-west-2.teo.dev.ascint.sabrecirrus.com:3128")
        self.proxyUrl           = ''
        self.influxQryTimeFrame     = os.environ.get('influxQryTimeFrame', "24h")

        self.VizFunctionName        = os.environ.get('VizFunctionName',         'lambda-dev-us-west-2-shp-get-viz-metrics-0000')
        self.ZabbixFunctionName     = os.environ.get('ZabbixFunctionName',      'lambda-dev-us-west-2-shp-get-zabbix-metrics-0000')
        self.PrometheusFunctionName = os.environ.get('PrometheusFunctionName',  'lambda-dev-us-west-2-shp-get-prometheus-metrics-0000')

        self.lambdaNameBySource = dict(prometheus = self.PrometheusFunctionName,
                                       zabbix     = self.ZabbixFunctionName,
                                       viz        = self.VizFunctionName
                                      )

    def dumpEnvironmentVars(self):

        loggger.debug(' Environment vars:')
        for key in self.__dict__.keys():
            loggger.debug(" {0:24} {1}".format(key + ":", self.__dict__[key]))

        return
