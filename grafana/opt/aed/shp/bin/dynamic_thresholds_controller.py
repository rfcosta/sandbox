#!/bin/env python3

import json

import glob
import sys
sys.path.append('/opt/aed/shp/lib')

import shputil

from service_configuration import ServiceConfiguration

import time
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

import os

def sync_from_s3_bucket(s3_dir, local_dir):
    os.system("aws s3 sync s3://" + s3_dir + '/ ' + local_dir + '/ --delete')


def sync_to_s3_bucket(local_dir, s3_dir):
    os.system("aws s3 sync " + local_dir + '/ s3://' + s3_dir + '/ --delete')


def task(service_name):
    log_dir = "/opt/aed/shp/dynamic-thresholds/threshold_history/"
    log_file = service_name + ".lastrun"
    log_file = log_file.replace(' ', '-')
    log_file = log_file.replace('/', '-')

    cmd = "python3" \
          " /opt/aed/shp/bin/compute_dynamic_thresholds.py --service_name \"" + service_name + "\""

#    logger.info("Spawn processor: " + cmd);
    os.system(cmd)
    return service_name


def spawn_threads():
    executor = ThreadPoolExecutor(multiprocessing.cpu_count())

    executors = []

    service_config = ServiceConfiguration()

    for service in service_config.get_services():
        state = service.state
        service_name = service.name

        logger.info("Service:" + service_name)
        executors.append(executor.submit(task, service_name))

    while True:
         still_running = 0
         for  executor in executors:
             if not executor.done():
                 still_running += 1
         # using print instead of logger to avoid buffering of the output
         print("Still running: " + str(still_running))

         if still_running == 0:
             break

         time.sleep(5)


# Delete 10 of the oldest seasonality cache files to force recomputation in batches
def cleanup_seasonality_cache(pattern):
    FILES_TO_DELETE = 10

    files = {}

    try:
        for path_to_file in glob.glob(pattern):
            stat = os.stat(path_to_file)
            files[stat.st_mtime] = path_to_file

        cnt = 0
        for file in sorted(files):
            cnt += 1
            if cnt > FILES_TO_DELETE:
                break
            os.remove(files[file])

    except Exception as e:
        logger.exception("Failed to cleanup seasonality cache")


config = shputil.get_config()

logger = shputil.get_logger("dynamicThresholds")

s3_data_dir = config['s3_dynamic_thresholds_dir']
s3_thresholds_data_dir = s3_data_dir + '/thresholds_history'

local_data_dir = config['local_dynamic_thresholds_dir']
local_thresholds_data_dir = local_data_dir + '/threshold_history'

if not os.path.isdir(local_data_dir):
    os.mkdir(local_data_dir, 0o777)

if not os.path.isdir(local_thresholds_data_dir):
    os.mkdir(local_thresholds_data_dir, 0o777)

sync_from_s3_bucket(s3_thresholds_data_dir, local_thresholds_data_dir)

cleanup_seasonality_cache(local_thresholds_data_dir + "/*-seasons.json")

spawn_threads()

sync_to_s3_bucket(local_thresholds_data_dir, s3_thresholds_data_dir)
