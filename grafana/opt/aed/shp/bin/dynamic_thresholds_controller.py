#!/bin/env python

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

    cmd = "/opt/aed/shp/bin/compute_dynamic_thresholds.py --service_name \"" + service_name + "\"" + " > " + log_dir + log_file + " 2>&1"

#    print cmd
    os.system(cmd)
    return service_name


def spawn_threads():
    executor = ThreadPoolExecutor(multiprocessing.cpu_count())

    executors = []

    service_config = ServiceConfiguration()

    for service in service_config.get_services():
        state = service.state
        service_name = service.name.encode('ascii','ignore')

        print "Service:", service_name
        executors.append(executor.submit(task, service_name))

    while True:
         still_running = 0
         for  executor in executors:
             if not executor.done():
                 still_running += 1
         print "Still running: ", still_running

         if still_running == 0:
             break

         time.sleep(5)

config = shputil.get_config()

s3_data_dir = config['s3_dynamic_thresholds_dir']
s3_thresholds_data_dir = s3_data_dir + '/thresholds_history'

local_data_dir = config['local_dynamic_thresholds_dir']
local_thresholds_data_dir = local_data_dir + '/threshold_history'

if not os.path.isdir(local_data_dir):
    os.mkdir(local_data_dir, 0777)

if not os.path.isdir(local_thresholds_data_dir):
    os.mkdir(local_thresholds_data_dir, 0777)

sync_from_s3_bucket(s3_thresholds_data_dir, local_thresholds_data_dir)

spawn_threads()

sync_to_s3_bucket(local_thresholds_data_dir, s3_thresholds_data_dir)
