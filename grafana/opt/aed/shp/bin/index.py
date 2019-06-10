
import os
import httplib
import uuid
import base64
import urlparse
import json

import sys
import datetime
import argparse
import requests
import re
import copy
import time
from operator import itemgetter


RANDOM = True
try:
    import random
except ImportError:
    RANDOM = False

from aws_util import AwsUtil
from zabbix_util import zabbixutil


#=============================================================
#  Environment setup for local test, doesn't execute on lambda
#=============================================================

AWS = AwsUtil(__name__)
loggger = AWS.loggger

# Get environment variables and decode passwords
#========================================================

ERRORS = 0
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
_NowUTC       = int(time.time())
_NowUTCMinute = int(_NowUTC) // 60 * 60

sqsUrl                         = os.environ['sqsUrl']
proxyURL                       = os.environ['proxyUrl']
s3Bucket_name                  = os.environ['s3Bucket_name']
zabbixAppsFileName             = os.environ['zabbixAppsFileName']
zabbixAccountName              = os.environ['zabbixAccountName']
zabbixUserName                 = os.environ['zabbixUserName']
zabbixAlternateUserName        = os.environ['zabbixAlternateUserName']
zabbixEncryptedHash            = os.environ['zabbixEncryptedHash']
zabbixAlternateEncryptedHash   = os.environ['zabbixAlternateEncryptedHash']
zabbixInstanceName             = os.environ['zabbixInstanceName']
zabbixURL1                     = os.environ['zabbixURL1']
zabbixURL2                     = os.environ['zabbixURL2']
zabbixServiceUser              = os.environ['zabbixServiceUser']
zabbixServiceEncryptedHash     = os.environ['zabbixServiceEncryptedHash']

(zabbixPassword, zabbixAlternatePassword,zabbixServicePassword) = AWS.getPasswords([zabbixEncryptedHash, zabbixAlternateEncryptedHash, zabbixServiceEncryptedHash],proxy=proxyURL)


#============================================================================================

def dumpEnvironmentVars():
    loggger.info('Environment vars:')
    loggger.info('- sqsUrl:                       ' + sqsUrl)
    loggger.info('- proxyURL:                     ' + proxyURL)
    loggger.info('- s3Bucket_name:                ' + s3Bucket_name)
    loggger.info('- zabbixzabbixAppsFileName:     ' + zabbixAppsFileName)
    loggger.info('- zabbixAccountName:            ' + zabbixAccountName)
    loggger.info('- zabbixUserName:               ' + zabbixUserName)
    loggger.info('- zabbixAlternateUserName:      ' + zabbixAlternateUserName)
    loggger.info('- zabbixPassword:               ' + AWS.conceal(zabbixPassword) )
    loggger.info('- zabbixAlternatePassword:      ' + AWS.conceal(zabbixAlternatePassword) )
    loggger.info('- zabbixEncryptedHash:          ' + zabbixEncryptedHash)
    loggger.info('- zabbixAlternateEncryptedHash: ' + zabbixAlternateEncryptedHash)
    loggger.info('- zabbixInstanceName:           ' + zabbixInstanceName)
    loggger.info('- zabbixURL1:                   ' + zabbixURL1)
    loggger.info('- zabbixURL2:                   ' + zabbixURL2)
    loggger.info('- zabbixServiceUser:            ' + zabbixServiceUser)
    loggger.info('- zabbixServiceEncryptedHash:   ' + zabbixServiceEncryptedHash)
    loggger.info('- zabbixServicePassword:        ' + AWS.conceal(zabbixServicePassword) )


    rightNowLocal = time.localtime()
    rightNowGMT   = time.gmtime()
    loggger.info('nowGMT=' + str(rightNowGMT))
    loggger.info('nowLCL=' + str(rightNowLocal))

    return


#===== END ENVIROMENT VARIABLES SETUP ==========================================================

# hasDatasource is used to filter servics that has a given data_source panel, in this case 'zabbix'
def hasDatasource(datas, panels):
    for panel in panels.values():
        if panel['data_source'] == datas:
            return True
    return False






def handler(event, context):
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
#    H A N D L E R
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =


    handler_clock_start = time.time()

    _backminutes = 10
    _backminutes = 4
    _PROTOCOL    = "http"

#=============================================================================
    # debug dump variables
    dumpEnvironmentVars()

    #  ----- Build a standard response -----
    if not 'StackId' in event:
        event['StackId'] = ''
    if not 'RequestId' in event:
        event['RequestId'] = ''
    if not 'LogicalResourceId' in event:
        event['LogicalResourceId'] = ''
    if not 'PhysicalResourceId' in event:
        event['PhysicalResourceId'] = ''

    response = {
      'StackId': event['StackId'],
      'RequestId': event['RequestId'],
      'LogicalResourceId': event['LogicalResourceId'],
      'Status': 'SUCCESS'
    }

    # PhysicalResourceId is meaningless here, but CloudFormation requires it
    if 'PhysicalResourceId' in event:
        response['PhysicalResourceId'] = event['PhysicalResourceId']
    else:
        response['PhysicalResourceId'] = str(uuid.uuid4())

    # ----- Determine Query time frame -----
    loggger.info("Determining the time frame")
    _nowUTC = int(time.time())
    _nowUTCMinute = int(_nowUTC) // 60 * 60
    time_till = _nowUTCMinute - 60
    time_from = time_till - ( (_backminutes - 1) * 60)
    loggger.info("Run fromTime: " + str( time_from       ) + " --> "  + str(AWS.epoch2date(time_from    )))
    loggger.info("Run toTime:   " + str( time_till       ) + " --> "  + str(AWS.epoch2date(time_till    )))
    loggger.info("Run nowTime:  " + str(_nowUTCMinute    ) + " --> " + str(AWS.epoch2date(_nowUTCMinute )))

# ----- Get Services from S3 -----
    servicesData = AWS.loadS3File(s3Bucket_name, zabbixAppsFileName, proxy=proxyURL)
    #loggger.debug("ServicesData: " + json.dumps(servicesData, indent=4))

    servicesObject = servicesData['result']
    zabbixServices = [service for service in servicesObject['services'].keys() if
                      hasDatasource('zabbix', servicesObject['services'][service]['panels'])]

    loggger.info("Services with data source Zabbix: " + str(zabbixServices))


    # Traverse Services with Panels with Zabbix input source
    # and create entries with meta data to query Zabbix for data
    # Multiple zabbix instances are supported as listed within each zabbix Service Health Portal Panel

    ZabbixDict   = {}    # Collection of metadata to fetch Zabbix data series
    InstancesAPI = []    # Array with ZabbixAPI instances objects for each o the required ones

    for service in zabbixServices:
        for _p in servicesObject['services'][service]['panels'].keys():
            _m = servicesObject['services'][service]['panels'][_p]
            if _m['data_source'] == 'zabbix':
                _zinstance = _m.get('zabbix_instance')
                _zhost     = _m.get('zabbix_host')
                _zkey      = _m.get('zabbix_key')
                _ztitle    = _m.get('title')
                _zservice  = service
                _zpanel    = _p

                _zinstance = None if _zinstance == "NONE" else _zinstance
                _zhost     = None if _zhost     == "NONE" else _zhost
                _zkey      = None if _zkey      == "NONE" else _zkey
                _ztitle    = None if _ztitle    == "NONE" else _ztitle

                _job = dict(host=_zhost, key=_zkey, title=_ztitle, service=_zservice, panel=_zpanel)

                if _zinstance and _zhost and _zkey and _ztitle:
                    loggger.info("Zabbix Metric: " + str(json.dumps(_job, indent=4)))

                    if not ZabbixDict.get(_zinstance):
                        _SERVER       = _PROTOCOL + "://" + _zinstance + ":443/zabbix"
                        _ZX           = zabbixutil(server=_SERVER)
                        _INSTANCEOK   = False
                        _APIVER       = None
                        try:
                            _APIVER = _ZX.api_version()
                            if _APIVER:
                                _INSTANCEOK = True
                                loggger.info("* Zabbix API version for %s: %s" % (_zinstance, _APIVER))
                            else:
                                loggger.error("* Zabbix API instance failed to get version for %s: %s" % (_zinstance, _APIVER))
                        except:
                            loggger.error("* Zabbix API instance failed to get version for %s: %s" % (_zinstance, _APIVER))

                        if _INSTANCEOK:
                            _LOGGED     = False
                            try:
                                _ZX.login(zabbixServiceUser,zabbixServicePassword)
                                _LOGGED = True
                            except Exception as _ERROR:
                                loggger.warn(zabbixAlternateUserName + " Zabbix Metrics Error on API: " + _ERROR.message())
                                pass

                            if not _LOGGED:
                                try:
                                    _ZX.login(zabbixAlternateUserName, zabbixAlternatePassword)
                                    _LOGGED = True
                                except Exception as err:
                                    loggger.error(zabbixUserName + " Zabbix login failed on " + _SERVER + ": " + err.message)

                            if _LOGGED:
                                _INSTANCENUM = InstancesAPI.__len__()
                                InstancesAPI.append(_ZX)
                            else:
                                _INSTANCENUM = None
                        else:
                            _INSTANCENUM = None

                        if _INSTANCENUM >= 0:
                            ZabbixDict[_zinstance] = dict(api=_INSTANCENUM, jobs=[])

                    if ZabbixDict.get(_zinstance):
                        _zx = InstancesAPI[ZabbixDict[_zinstance].get("api")]
                        _items = _zx.getHostItems(10, _zhost, _zkey)
                        loggger.debug("---> ITEMS: " + json.dumps(_items, indent=4))
                        if len(_items) > 0:
                            _item = _items[0]
                            _job["item"] = _item

                        ZabbixDict[_zinstance]["jobs"].append(_job)
                    else:
                        loggger.warn("Metric skipped due a problem logging on Zabbix instance: " + _SERVER)

    loggger.debug("Zabbix Jobs: " + json.dumps(ZabbixDict, indent=4))


    def convert2shpAPI(job, _time_from, _time_till):
        loggger.debug("Converting job: " + json.dumps(job, indent=4))
        shpAPIrequest = dict(
            metrics=[],
            kpi="True",
            precision="s",
            api_version="4",
            source="zabbix"
        )

        ZXDATA = sorted([dict(minute=zitem['minute'], value=zitem['value']) for zitem in job['data']],
                         key=itemgetter('minute'), reverse=True
                         )

        loggger.debug("*" * 10 + " ZXDATA " + "*" * 10)
        loggger.debug(json.dumps(ZXDATA, indent=4))

        _minute = _time_till
        ZXI = 0
        while _minute >= _time_from:
            while (ZXDATA[ZXI]['minute'] > _minute):
                loggger.debug("_minute = " + str(_minute) +
                      " ZXI=" + str(ZXI) +
                      " ZXDATA[" + str(ZXI) + "]['minute'] = " + str(ZXDATA[ZXI]['minute'])
                      )
                ZXI += 1

            shpAPIrequest['metrics'].append(dict(
                ci=job['service'],
                key=job['panel'],
                time=_minute,
                value=ZXDATA[ZXI]['value']
                )
            )
            _minute -= 60


        return shpAPIrequest




    def processJob(instance, api, job, _timeFrom, _timeTill):
        _delay = int(job['item']['delay'])
        if (_delay > 60):
            _xtimeFrom = _timeFrom - _delay
        _DATAITEMS = api.getHistory(job["item"], time_from=_xtimeFrom, time_till=_timeTill)
        job["data"] = _DATAITEMS
        shpReqs = convert2shpAPI(job, _timeFrom, _timeTill)

        return shpReqs

# ============================================================================================
# ============================================================================================
# ==================  R U N   J O B S  =======================================================
# ============================================================================================
# ============================================================================================

    for _ZINSTANCE in ZabbixDict:
        _ZXUTIL = InstancesAPI[ZabbixDict[_ZINSTANCE]["api"]]
        for _JOB in ZabbixDict[_ZINSTANCE]["jobs"]:
            try:
                _SHPrequest = processJob (_ZINSTANCE, _ZXUTIL, _JOB, time_from, time_till)
                loggger.debug("Zabbix SHP: " + json.dumps(_SHPrequest, indent=4))
                _status = AWS.send_shp_request(sqsUrl, _SHPrequest, proxy=proxyURL, replication=True)
                loggger.debug("Enqueue STATUS " + _status)
            except Exception as e:
                loggger.error("Zabbix SHP: processJob or send failed: " + str(e.message))



# ============================================================================================
# ======  SHOW PROCESS STATISTICS  ===========================================================
# ============================================================================================

    handler_clock_end    = time.time()
    handler_clock_duration = (int(handler_clock_end * 100) - int(handler_clock_start * 100))

    loggger.info("*** START / STOP:   " + str(handler_clock_start)            + " --> " + str(handler_clock_end) + " ***")
    loggger.info("*** CLOCK DURATION: " + str(handler_clock_duration / 100.0) + "  SECONDS ***")

    loggger.info("*** END OF LAMBDA " + response['Status'] + ", ERRORS=" + str(ERRORS))

#============================================================================================

    return AWS.send_response(event, response)



