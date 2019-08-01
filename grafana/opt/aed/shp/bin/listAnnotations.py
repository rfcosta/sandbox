#!/bin/env python

import urllib
import calendar
import os
import copy
import json
import sys
from datetime import datetime
from optparse import OptionParser
import logging
from logging import getLogger, DEBUG, INFO, WARNING, ERROR

sys.path.append('/opt/aed/shp/lib')
sys.path.append('/opt/aed/shp/lib/grafana')

import shputil
from helper import Helper

class AlertAnnotationUtil():

    LOG_LEVEL_DEFAULT = DEBUG
    NAME_DEFAULT = __name__
    INSTANCE_DEFAULT = "sabredev2"

    @staticmethod
    def encode(service):
        service_name = service.replace(" -", "-")
        service_name = service_name.replace("- ", "-")
        service_name = service_name.replace("_", "-")
        service_name = service_name.replace(" ", "-")
        return service_name

    @staticmethod
    def convert_utc_to_epoch(timestamp_string):
        '''Use this function to convert utc to epoch'''
        print (timestamp_string)
        try:
            timestamp = datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%S:%fZ')
        except Exception:
            try:
                timestamp = datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%S.%fZ')
            except Exception:
                timestamp = datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%SZ')

        epoch = int(calendar.timegm(timestamp.utctimetuple()))
        print (epoch)
        return str(epoch) + '000000000'


    @staticmethod
    def LoadJson(json_filename):
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
        if kwargs.get("panelids",True):
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

    def updateAnnotationPair(self, annotationRequest, region, **kwargs):

        # Verify if we need to perform 2 updates
        returnText = ''
        annotationId = region[0]['id']
        try:
            aupdatedata = dict(text     = annotationRequest['text'],
                               time     = annotationRequest['time'],
                               isRegion = annotationRequest['isRegion'],
                               timeEnd  = annotationRequest['timeEnd'],
                               tags     = annotationRequest['tags']
                               )
            _updateResponse = self.helper.api_put_with_data('annotations/' + str(annotationId), aupdatedata)
            returnText = str(_updateResponse.text)

        except Exception as E:
            self.loggger.warn("#updateAnnotationPair> Exception: " + str(E.message))
            returnText = str(E.message)
            pass

        return returnText

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
            self.loggger.warn("#updateAnnotation> Exception: " + str(E.message))
            returnText = str(E.message)
            pass

        return returnText



    @staticmethod
    def annotationRequest(*args, **kwargs):

        _dashboardId    = kwargs.get("dashboardId")
        _panelId        = kwargs.get("panelId")
        _time           = kwargs.get("time")
        _timeEnd        = kwargs.get("timeEnd")
        _isRegion       = True
        if not _timeEnd:
            _isRegion = False

        _text           = kwargs.get("text")
        _title          = kwargs.get("title")
        _tags           = kwargs.get("tags")

        if not _dashboardId:
            raise Exception("#annotationRequest: Missing dashboardId=")
        if not _panelId:
            raise Exception("#annotationRequest: Missing panelId=")
        if not _time:
            raise Exception("#annotationRequest: Missing time=")
        if not _text:
            raise Exception("#annotationRequest: Missing text=")
        if not _tags:
            _tags = []

        if not _title:
            _title = ''

        _annotationReq = {
            "dashboardId":  _dashboardId,
            "panelId":      _panelId,
            "time":         _time,          # int(change['start_datetime']),
            "isRegion":     _isRegion,
            "timeEnd":      _timeEnd,       # int(change['end_datetime']),
            "tags":         _tags,          # [change['number']],
            "title":        _title,         # change['number'] + " " + change['short_description'],
            "text":         _text
        }

        return _annotationReq

    def makeURI(self, type='incident', sys_id='', number='', short_description=''):

        if not type or not sys_id or not number or not short_description:
            raise Exception ("makeURI missing parameters")
        pass

        _URI = "<a target=\"_blank\" href='https://{0}.service-now.com/{1}.do?sys_id={2}'>{3}</a>: {4}".format(
               self.instanceName, type, sys_id, number, short_description
               )

        return _URI

if __name__ == "__main__":

    parser = OptionParser(add_help_option=False)
    parser.add_option("-h", "--help",      action="help")
    parser.add_option("-o", "--options",   dest="options_file", help="Options json file", default='')
    parser.add_option("-i", "--instance",  dest="instance"   , help="SNOW Instance"    ,  default="sabredev2")
    parser.add_option("-f", "--file",      dest="jsonFile"    , help="Output json file",  default='listAnnotations.json')
    parser.add_option("-d", "--dashboard", dest="dashboardId", help="Dashboard Id"     ,  default="220")
    parser.add_option("-a", "--panel",     dest="panelId",     help="Panel Id"         ,  default="2")
    parser.add_option("-r", "--org",       dest="orgId"      , help="Org Id"           ,  default="2")
    parser.add_option("-t", "--time",      dest="time"       , help="From Time"        ,  default="1564598378")
    parser.add_option("-e", "--timeEnd",   dest="timeEnd"    , help="To Time"          ,  default="1564598378")
    parser.add_option("-g", "--grafana",   dest="grafana"    , help="Grafana Instance" ,  default="localhost")
    parser.add_option("-p", "--port",      dest="port"       , help="Grafana Port"     ,  default="3000")
    parser.add_option("-l", "--limit",     dest="limit"      , help="Limit of records" ,  default="100" )
    parser.add_option("-u", "--user",      dest="user"       , help="Grafana User"      , default='Admin')
    parser.add_option("-w", "--password",  dest="pswd"       , help="Grafana Password"  , default='IamApass01')


    (options, args) = parser.parse_args()

    # ----------------------------------------------------------------------------------------------------------
    # The following statement is just to ilustrate how to address the attributes of an object like a dictionary
    #       options.__dict__['source'] = 'VIZ' if not options.source else options.source
    # ----------------------------------------------------------------------------------------------------------

    options_from_json = dict()
    if options.options_file:
        options_from_json = AlertAnnotationUtil.LoadJson(options.options_file)

    # The following onlyt works on Python 2:
    # options_from_json.update(  (ky, val) for (ky,val) in options.__dict__.iteritems() if val  )

    options_from_json.update(  (ky, val) for (ky,val) in options.__dict__.items() if val  )


    #update back options after the overides
    options.__dict__.update(options_from_json)

    print("Options: " + str(options))

    if  not options.user or \
        not options.pswd or \
        not options.instance or \
        not options.port or \
        not options.orgId or \
        not options.limit or \
        not options.dashboardId or \
        not options.port:
        print("**ERROR** All options user/pswd/instance/port/orgId/limit/dashboard/ port must be specified from command options + options_file (-o or --options_file)")
        exit(8)

    options.regionId = 0
    URLTEMPLATE = "http://{0}:{1}@{2}:{3}/api/annotations/?orgId={4}&limit={5}&dashboardId={6}&regionId={7}"
    # &type={8}"
    grafana_url = URLTEMPLATE.format(
        options.user,
        options.pswd,
        options.grafana,
        options.port,
        options.orgId,
        options.limit,
        options.dashboardId,
        options.regionId
    )

    print (grafana_url)

    _example_dashboardId = 220
    _example_panelId     = 2

    autl = AlertAnnotationUtil(orgId=options.orgId, instanceName=options.instance)

    _dashAnnotations = autl.getAnnotationsOnDashboardPanel(dashboardId=options.dashboardId, \
                                                           panelId=options.panelId, \
                                                           fromTime=options.time, toTime=options.timeEnd \
                                                          )
    _numberOfAnnotationsReturned = len(_dashAnnotations)

    autl.loggger.info("** Ann returned %d" % (_numberOfAnnotationsReturned))

    _incident   = 'INC2543646'
    _instance   = 'sabredev2'
    _inc_sys_id = 'b3783ae8dbcffb0821421ffa6896194d'
    _inc_descr  = '[Alert3450155] Service Health Portal: WARNING: Payment Internet Payment Engine Transaction Count is 35 which is below the dynamic threshold'

    _annotation = copy.deepcopy(_dashAnnotations[0])
    _annotation['text'] = autl.makeURI(sys_id=_inc_sys_id, number=_incident, short_description=_inc_descr)



    response = autl.updateAnnotation( _annotation )

