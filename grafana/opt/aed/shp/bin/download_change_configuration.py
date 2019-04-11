#!/bin/env python

import sys
import os
import logging

sys.path.append('/opt/aed/shp/lib')

import shputil

s3_file_path = '/cache/ChgConfiguration.json'

config = shputil.get_config()
shputil.configure_logging(config["logging_configuration_file"])

target_file = config['change_configuration_file']

s3Bucket = config['aws_s3_bucket']

ret_code = os.system('aws s3 cp ' + s3Bucket + s3_file_path + ' ' + target_file + " >/dev/null")

if (ret_code == 0):
   logging.info("Successfully downloaded change configuration file from S3")
else:
   logging.error("Failed to download change configuration file from S3")
