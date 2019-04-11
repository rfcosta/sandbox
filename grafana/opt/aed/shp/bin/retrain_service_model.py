#!/bin/env python

# This script will create a flag file in the S3 bucket.  When dynamic thresholds get calculated later,
# it will look for this file based on service, key and metric.  If it exists, it will retrain the model.

# ./retrain_service_model.py  --service="GetThere US Government" --key=avg_processing_time --metric=avg_processing_time

import sys
import boto3
import botocore

from optparse import OptionParser

sys.path.append('/opt/aed/shp/lib')
sys.path.append('../lib')

from service_configuration import ServiceConfiguration
import shputil

parser = OptionParser()
parser.add_option("--service", dest="service", default="")
parser.add_option("--key", dest="key", default="")
parser.add_option("--metric", dest="metric", default="")
(options, args) = parser.parse_args()


def file_exist_in_s3(filename):
    try:
        s3 = boto3.resource('s3')
        s3.Object(s3_bucket_name, filename).load()
    except botocore.exceptions.ClientError as e:
        print "Unable to locate:", s3_bucket_name + '/' + filename
        raise Exception("Cannot find cached training data in s3 bucket.  You may have entered incorrect arguments.")
    return True


def create_flag_file(filename):
    s3 = boto3.resource('s3')
    print "Creating: ", s3_bucket_name, filename
    object = s3.Object(s3_bucket_name, filename)
    object.put(Body='retrain me')

try:
    service = options.service
    key = options.key
    metric = options.metric

    if not service or not key or not metric:
        raise Exception("Missing or invalid argument.  To see available options, rerun this script with -h or --help")

    config = shputil.get_config()

    local_training_data_dir = config['local_dynamic_thresholds_dir'] + "/training-data"
    s3_bucket_name = config['aws_s3_bucket'].replace("s3://", "")

    service_config = ServiceConfiguration()

    services = []
    for service in service_config.get_services():
        if service.state != 'undefined':
            service.name = service.name.replace('/', ' ')
            services.append(service.name)

    if options.service not in services:
        raise Exception("Service not found: ", options.service)

    cache_id = options.service + '-' + options.metric + '-' + options.key
    if file_exist_in_s3('dynamic-thresholds/training-data/' + cache_id + '.pcl'):
       create_flag_file('dynamic-thresholds/flags/' + cache_id + '.retrain')

except Exception, e:
    print e
