#!/bin/env python3

import sys
import os

sys.path.append('/opt/aed/shp/lib')

import shputil

shputil.check_logged_in_user('centos')

s3_file_path = '/cache/ChgConfiguration.json'

config = shputil.get_config()
logger = shputil.get_logger("shp")

target_file = config['change_configuration_file']

s3Bucket = config['aws_s3_bucket']

ret_code = os.system('aws s3 cp ' + s3Bucket + s3_file_path + ' ' + target_file + " >/dev/null")

if (ret_code == 0):
   logger.info("Successfully downloaded change configuration file from S3")
else:
   logger.error("Failed to download change configuration file from S3")
