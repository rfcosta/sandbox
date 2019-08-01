import urllib
import calendar
import os
import copy
import json
import sys
import time
from datetime import datetime
import logging
from logging import getLogger, DEBUG, INFO, WARNING, ERROR

sys.path.append('/opt/aed/shp/lib')
sys.path.append('/opt/aed/shp/lib/grafana')

import shputil
from helper import Helper



class AlertAnnotationUtil:

    LOG_LEVEL_DEFAULT = DEBUG
    NAME_DEFAULT = __name__
    INSTANCE_DEFAULT = "sabredev2"

    @classmethod
    def encode(cls, service):
        service_name = service.replace(" -", "-")
        service_name = service_name.replace("- ", "-")
        service_name = service_name.replace("_", "-")
        service_name = service_name.replace(" ", "-")
        return service_name

    @classmethod
    def convert_utc_to_epoch(cls, timestamp_string):
        '''Use this function to convert utc to epoch'''
        try:
            timestamp = datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%S:%fZ')
        except Exception:
            try:
                timestamp = datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%S.%fZ')
            except Exception:
                timestamp = datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%SZ')

        epoch = int(calendar.timegm(timestamp.utctimetuple()))
        return str(epoch) + '000000000'


    @classmethod
    def LoadJson(cls, json_filename):
        """Load JSON file.
        Raises ValueError if JSON is invalid.

        :filename: path to file containing query
        :returns: dic
        """
        try:
            with open(json_filename) as json_file:
                return json.load(json_file)
        except ValueError as err:
            return dict()

    @classmethod
    def epoch2date(cls, epoch):
        return datetime.datetime.fromtimestamp(float(epoch // 1000))

    @classmethod
    def epochMinute(cls, epoch):
        return int(epoch) // 60 * 60

    @classmethod
    def conceal(cls, pwd):
        return pwd[0].ljust(pwd.__len__(), '*') + pwd[-1]


    @classmethod
    def TimeNow(cls):
        return int(time.time())

    @classmethod
    def TimeInterval(cls, _nowUTC, _minutes):

        _nowUTCMinute = cls.epochMinute(_nowUTC)
        _backUTCMinute = _nowUTCMinute - _minutes * 60

        return (_backUTCMinute, _nowUTCMinute)

    @classmethod
    def TimeIntervalNow(cls, _minutes):
        return cls.TimeInterval(cls.TimeNow(), _minutes)



    def __init__(self, *args, **kwargs):

        _myname   = kwargs.get('myname',self.NAME_DEFAULT)
        _loglevel = kwargs.get('loglevel',self.LOG_LEVEL_DEFAULT)
        _panelids = kwargs.get('panelids',True)
        _orgId    = kwargs.get('orgId',1)
        _instanceName = kwargs.get('instanceName', self.INSTANCE_DEFAULT)

        self.helper = Helper(_orgId)
        self.orgId = _orgId
        self.instanceName = _instanceName
        self.reset()
        _logger = getLogger(_myname + str(self.orgId))

        if _logger.handlers.__len__() == 0:
            _logger.propagate = 0
            _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s %(funcName)s:%(lineno)d: %(message)s')
            _console_handler = logging.StreamHandler()
            _console_handler.setFormatter(_formatter)
            _logger.addHandler(_console_handler)

        self.loggger = _logger
        self.loggger.setLevel(_loglevel)

        self.loggger.debug("Util init start for org %s" % (str(self.orgId)))
        self.CONFIG = shputil.get_config()
        self.CONFIG_FILE_NAME = self.CONFIG.get('service_configuration_file')
        self.CHANGE_FILE_NAME = self.CONFIG.get('change_configuration_file')
        self.dashboardList = self.getDashboards(panelids=_panelids)

        _logger.debug("Util init end for org %s, %d dashboards found" % (str(self.orgId), len(self.dashboardList)))


    def reset(self):
        self.limit = 20000
        self.limitReached = True
        self.testMode = False
        self.existingAnnotations = dict() # indexed by (dashboardId, panelId, hash)


    def getOrgs(self):
        resp = self.helper.api_get_with_params("orgs", {})
        organizations = json.loads(resp.content)
        return organizations


    def getPanelidsFromDashboard(self,uid):
        panelids = []

        if uid:
            itemResp = self.helper.api_get_with_params("dashboards/uid/" + uid, {})
            dashboardItem = json.loads(itemResp.content)
            panels = dashboardItem['dashboard']['panels']
            panelids = [p['id'] for p in panels]

        return panelids


    def getDashboards(self, *args, **kwargs):
        resp = self.helper.api_get_with_params("search", {'type': 'dash-db'})
        dashboards = json.loads(resp.content)
        if kwargs.get("panelids",False):
            for dashboard in dashboards:
                dashboard['panelids'] = self.getPanelidsFromDashboard(dashboard['uid'])
        return dashboards


    def getAnnotationsOnDashboard(self, *args, **kwargs):
        _annotationsFromGrafana = []
        if kwargs.get('dashboardId'):
            params = dict(type='annotation',
                          dashboardId=kwargs.get('dashboardId',0),
                          limit=kwargs.get('limit',self.limit)
                          )

            _from = kwargs.get('fromTime')
            _to = kwargs.get('toTime')
            if _from:
                params['from'] = str(_from) + '000'
            if _to:
                params['to'] = str(_to) + '999'

            resp = self.helper.api_get_with_params("annotations", params)
            _annotationsFromGrafana = json.loads(resp.content)

        return _annotationsFromGrafana


    def getAnnotationsOnDashboardPanel(self, *args, **kwargs):
        _annotationsFromGrafana = []
        if kwargs.get('dashboardId') and kwargs.get('panelId'):
            params = dict(type='annotation',
                          dashboardId= kwargs.get('dashboardId',0),
                          panelId    = kwargs.get('panelId',0),
                          limit      = kwargs.get('limit',self.limit)
                          )
            _from = kwargs.get('fromTime')
            _to   = kwargs.get('toTime')
            if _from:
                params['from'] = str(_from) + '000'
            if _to:
                params['to']   = str(_to)   + '999'


            resp = self.helper.api_get_with_params("annotations", params)
            _annotationsFromGrafana = json.loads(resp.content)
        return _annotationsFromGrafana


    def updateAnnotation(self, annotation, **kwargs):

        # Verify if we need to perform 2 updates
        returnText = ''
        annotationId = annotation['id']
        try:
            aupdatedata = dict(text     = annotation['text'],
                               time     = annotation['time'],
                               isRegion = False,
                               tags     = annotation['tags']
                               )
            _updateResponse = self.helper.api_put_with_data('annotations/' + str(annotationId), aupdatedata)
            returnText = str(_updateResponse.text)

        except Exception as E:
            self.loggger.warn("Exception: " + str(E.message))
            returnText = str(E.message)
            pass

        return returnText


    def makeSnowHTMLReference(self, type='incident', sys_id='', number='', short_description=''):

        if not type or not sys_id or not number or not short_description:
            raise Exception ("makeSnowHTMLReference: missing parameters")
        pass

        _REF = "<a target=\"_blank\" href='https://{0}.service-now.com/{1}.do?sys_id={2}'>{3}</a>: {4}".format(
               self.instanceName, type, sys_id, number, short_description
               )

        return _REF

