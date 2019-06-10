
import boto3

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

from zabbix_api import ZabbixAPI
from aws_util   import AwsUtil


import sys
import os
import json
import datetime
import argparse
import base64
import requests
import re
import copy
import time

AWS = AwsUtil(__name__)
loggger = AWS.loggger

class zabbixutil(object):
    """Encapsulates utilities for Zabbix API calls
    """



    def __init__(self, *args, **kwargs):

        self.JSON = False

        server  = kwargs.get('server')
        user    = kwargs.get('user')
        passw   = kwargs.get('password')

        if server:
            self._server = server
        if user:
            self._user = user
        if passw:
            self._password = passw
        else:
            self.password = ''

        self._XHEADER   = re.compile('[,]+')
        self._XDATETIME = re.compile('\d\d\d\d[-]\d\d[-]\d\d\s\d\d[:]\S+')
        self._XCSV      = re.compile('([^,]+)[,]?|[,]')
        self._XIGN      = re.compile(r'^$|^\s+$|Process finished with exit code')
        self._XCOLON    = re.compile('\:')

        self.zxapiversion = None
        try:
            self.zx = ZabbixAPI(server=self._server)
            self.zxapiversion = self.zx.api_version()
        except Exception as err:
            loggger.error("** ERROR GETTING API VERSION: " + str(self.zxapiversion) + " ERR: " + str(err.message))


        self._DASHLINE = "=" * 60
        self._OUTPUT_PARAMS = {'output': ZabbixAPI.QUERY_EXTEND}


    def api_version(self):
        return self.zxapiversion


    def login(self,user,password):
        try:
            self.zx.login(user,password)
        except Exception as ex:
            raise ex


    @staticmethod
    def ItemTypes():
        return {
            "0": "Numeric(float)   ",
            "1": "Character        ",
            "2": "Log              ",
            "3": "Numeric(unsigned)",
            "4": "Text             "
        }

    def printHostItems(self, _ITEMS):
        _TYPES = self.ItemTypes()
        _host = ''
        _itemslen = _ITEMS.__len__()
        if _itemslen > 0:
            _host = _ITEMS[0]['hostid']

        loggger.info(self._DASHLINE)

        _SCFMT = "%8s | %8s  | %10s | %10s | %-40s | %-s | %-s  |  %8s  | ITEMS %-s"


        loggger.info("--- ITEMS FROM HOST " + str(_host) + " (items " + str(_itemslen) + ") ---")
        loggger.info(_SCFMT % (
            "ITEMID", "HOSTID", "HISTORY", "DELAY", "NAME".ljust(80), "KEY".ljust(60), "VALUE TYPE          ", "ORD", "DESCRIPTION") )

        _count = 0
        for _ITEM in _ITEMS:
            _count += 1
            _value_type = _ITEM.get("value_type")
            _display_type = _value_type + ": " + _TYPES.get(_value_type)
            loggger.info(_SCFMT % (
                _ITEM["itemid"], _ITEM["hostid"], _ITEM["history"], _ITEM["delay"], _ITEM["name"].ljust(80), _ITEM.get("key_").ljust(60),
                _display_type, str(_count), _ITEM.get("description"))
            )

        if self.JSON:
            _limit = 2
            loggger.info("--- ITEMS JSON (Limited to " + str(_limit) + ") ---")
            loggger.info(json.dumps(_ITEMS[0:_limit], indent=4))


    #=====================================================================

    def getHostItems(self, _limit=5, _host=0, _key=0, _hostids=0):

        _ITPARAMS = {"output": self._OUTPUT_PARAMS["output"], "limit": _limit, "sortfield": "name"}

        if _host > 0:
            _ITPARAMS["host"] = _host

        if _hostids > 0:
            _ITPARAMS["hostids"] = _hostids

        if _key:
            _ITPARAMS["search"] = {"key_": _key}

        loggger.debug("HostItems: " + json.dumps(_ITPARAMS, indent=4))

        _ITEMS = self.zx.item.get(_ITPARAMS)

        return _ITEMS

    def printUsers(self, _USERS):
        loggger.info(self._DASHLINE)

        _UFMT = "%3s  %-24s  %-24s  %-s "
        loggger.info("--- USERS ---")
        loggger.info(_UFMT % ("UID","ALIAS","NAME","SURNAME") )
        for user in _USERS:
            loggger.info(_UFMT % (user["userid"], user["alias"], user["name"], user["surname"]))


    def getUsers(self):
        #ret1 = self.zx.call('user.get', _OUTPUT_PARAMS)
        _USERS = self.zx.user.get({'output': ZabbixAPI.QUERY_EXTEND})

        return _USERS

    def getHistory(self, ITEM, limit=50, time_from='', time_till='' ):

        _nowUTC         = int(time.time())
        _nowUTCMinute   = int(_nowUTC) // 60 * 60

        if not time_from:
            time_from = _nowUTCMinute - (limit * 60) - int(ITEM["delay"])

        if not time_till:
            time_till = _nowUTCMinute

        HISTORYPARMS = {"history": ITEM["value_type"],
                        "hostids": [ITEM['hostid']],
                        "itemids": [ITEM["itemid"]],
                        "time_from": time_from,  # 1549035094,
                        "time_till": time_till,
                        #"limit": limit,
                        "output": "extend",
                        "sortfield": "clock",
                        "sortorder": ZabbixAPI.SORT_DESC
                        }
        loggger.debug("*** HISTORY PARMS: " + json.dumps(HISTORYPARMS, indent=4))

        _ITEMS = self.zx.history.get(HISTORYPARMS)

        for _ITEM in _ITEMS:
            _ITEM['minute'] = int(_ITEM['clock']) // 60 * 60

        return _ITEMS


    def printHistory(self, _ITEMS):
        loggger.info("")
        loggger.info(self._DASHLINE)
        _FMT = " %10s | %10s | %-19s | %10s | %-19s | %8s | %9s | %s"
        loggger.info(_FMT % ("Ord", "Clock", "Timestamp", "MinClock", "Minute", "Itemid", "NS", "Value") )
        loggger.info(_FMT % ("---", "-"*10, "-"*19, "-"*10, "-"*19, "-"*8, "-"*9, "-"*20) )

        _ord = 0
        for _ITEM in _ITEMS:
            _itemid = _ITEM.get("itemid")
            _ns     = _ITEM.get("ns")
            _value  = _ITEM.get("value")
            _clock  = _ITEM.get("clock")
            _timestamp = str(AWS.epoch2date(_clock))
            _minute_clock = AWS.epochMinute(_clock)
            _minutestamp  = str(AWS.epoch2date(_minute_clock))
            _ord += 1

            loggger.info(_FMT % (_ord, _clock, _timestamp, _minute_clock, _minutestamp, _itemid, _ns, _value) )


