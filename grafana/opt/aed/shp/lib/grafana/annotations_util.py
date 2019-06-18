#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import json
import requests
import traceback
import time
import datetime
import re
from requests.auth import HTTPBasicAuth
from retrying import retry

import logging
from logging  import getLogger, DEBUG, INFO, WARNING, ERROR



sys.path.append('/opt/aed/shp/lib')
sys.path.append('/opt/aed/shp/lib/grafana')

import shputil
from helper import Helper


class AnnotationsUtil():

    LOG_LEVEL_DEFAULT = DEBUG
    NAME_DEFAULT = __name__

    def __init__(self, org_id,myname=NAME_DEFAULT,loglevel=LOG_LEVEL_DEFAULT):
        self.helper = Helper(org_id)
        self.orgId = org_id
        self.reset()
        _logger = getLogger(myname + str(self.orgId))

        if _logger.handlers.__len__() == 0:
            _logger.propagate = 0
            _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s %(funcName)s:%(lineno)d: %(message)s')
            _console_handler = logging.StreamHandler()
            _console_handler.setFormatter(_formatter)
            _logger.addHandler(_console_handler)

        self.loggger = _logger
        self.loggger.setLevel(loglevel)


    def reset(self):
        self.limit = 20000
        self.limitReached = True
        self.testMode = False
        self.existingAnnotations = dict() # indexed by (dashboardId, panelId, hash)

    def setLimitStatus(self,state=True):
        self.limitReached = state
        if state:
            self.loggger.warn("** Limit Reached Status set to " + str(self.limitReached) )

    @staticmethod
    def epoch2date(epoch):
        return datetime.datetime.fromtimestamp(float(epoch // 1000))

    @staticmethod
    def epochMinute(epoch):
        return int(epoch) // 60 * 60

    @staticmethod
    def conceal(pwd):
        return pwd[0].ljust(pwd.__len__(), '*') + pwd[-1]

    @staticmethod
    def LoadFile(filename):
        """Load JSON file.
        Raises ValueError if JSON is invalid.

        :filename: path to file containing query
        :returns: dic
        """
        try:
            with open(filename) as query_file:
                return json.load(query_file)
        except ValueError as err:
            return dict()

    @staticmethod
    def WriteFile(filename, object, option="w"):
        """Load JSON file.
        Raises ValueError if JSON is invalid.

        :filename: path to file containing query
        :returns: dic
        """
        try:
            with open(filename, option) as out_file:
                out_file.write(json.dumps(object, indent=4))
            out_file.close()
            return ''
        except Exception as err:
            return err.message

    @staticmethod
    def parseSysId(_text):
        _sysId = ''
        _XSYSID = re.compile('https[:][/][/]\S+\?sys_id=([0123456789abcdef]{32})')
        if _text:
            _tokens = _XSYSID.findall(_text)
            if _tokens.__len__() > 0:
                _sysId = _tokens[0]
        return _sysId

    @staticmethod
    def parseChange(_text):
        _change = ''
        _XCHANG = re.compile('https[:][/][/]\S+\?sys_id=[0123456789abcdef]{32}.+CHG(\d+)')
        #_text = _annotation.get('text')
        if _text:
            _tokens = _XCHANG.findall(_text)
            if _tokens.__len__() > 0:
                _change = _tokens[0]
        return 'CHG' + _change

    @staticmethod
    def regionRequest(*args, **kwargs):

        _regionRequest = dict(
            dashboardId    = kwargs.get("dashboardId"),
            panelId        = kwargs.get("panelId"),
            time           = kwargs.get("time"),
            timeEnd        = kwargs.get("timeEnd"),
            isRegion       = True,
            text           = kwargs.get("text"),
            title          = kwargs.get("title",''),
            tags           = kwargs.get("tags",[])
        )

        for p in ['dashboardId','panelId','time','timeEnd','text','isRegion']:
            if not _regionRequest[p]:
                raise Exception("#Annotations.regionRequest: Missing %s" % (p))

        return _regionRequest

    def addAnnotationToExisting(self, grafanaAnnotation, dupes=False):
        _text = grafanaAnnotation.get('text',None)
        if _text:
            _hash = self.parseSysId(_text)
            _key = (grafanaAnnotation['dashboardId'], grafanaAnnotation['panelId'], _hash)


            self.existingAnnotations.setdefault(_key,dict())

            _regionId = grafanaAnnotation['regionId']
            _changeOnPanel = self.existingAnnotations[_key]

            _ignore = False
            _changeOnPanel.setdefault(_regionId,[])

            if not dupes:
                _latestRegionId = max(_changeOnPanel.keys())

                for _rId in _changeOnPanel.keys():
                    if _rId != _latestRegionId:
                        del _changeOnPanel[_rId]
                    pass
                pass
            pass

            if _regionId in _changeOnPanel:
                _annotationSubset = dict(id=None, time=None, dashboardId=None, panelId=None, regionId=None)
                dictSetValues = lambda x, y: dict([(i, x[i]) for i in x if i in set(y)])
                _annotationSubset = dictSetValues(grafanaAnnotation, set(_annotationSubset))

                _change = self.parseChange(_text)
                _annotationSubset['change'] = _change

                if len(_changeOnPanel[_regionId]) > 0 and _annotationSubset['id'] > _changeOnPanel[_regionId][0]['id']:
                    _changeOnPanel[_regionId].append(_annotationSubset)
                else:
                    _changeOnPanel[_regionId].insert(0,_annotationSubset)


            return _changeOnPanel[_regionId]

        return False


    def getExistingChangesOnPanelFromDashboard(self):
        return self.existingAnnotations.keys()


    def printExistingAnnotation(self, key):
        _dashboardId, _panelId, hash = key

        for _regionId in self.existingAnnotations[key].keys():
            _region =  self.existingAnnotations[key][_regionId]
            _numberOfAnnotations = len(_region)
            if _numberOfAnnotations == 2:
                _annotation1 = json.dumps(_region[0])
                _annotation2 = json.dumps(_region[1])

                self.loggger.info("# Dash %8d Panel %8d Hash %-32s Region %8d A1: %s A2: %s" %
                        ( _dashboardId, _panelId, hash, _regionId,
                          _annotation1, _annotation2
                        )
                      )

    def printAllExistingAnnotations(self):

        for _key in self.getExistingChangesOnPanelFromDashboard():
            self.printExistingAnnotation(_key)


    def loadAnnotationsReturnedFromGrafana(self, annotations):
        for _annotation in annotations:
            self.addAnnotationToExisting(_annotation, dupes=True)
        return True

    def loadLatestAnnotationsReturnedFromGrafana(self, annotations):
        for _annotation in annotations:
            self.addAnnotationToExisting(_annotation, dupes=False)
        return True


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
                          limit=kwargs.get('limit',20000)
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
                          limit      = kwargs.get('limit',20000)
                          )

            resp = self.helper.api_get_with_params("annotations", params)
            _annotationsFromGrafana = json.loads(resp.content)
        return _annotationsFromGrafana


    def deleteAnnotationByRegion(self,region):
        params = dict(orgId=self.orgId)
        resp = self.helper.api_delete("annotations/region/" + str(region))
        if resp.status_code != 200:
            raise Exception("Error deleting annotation " + str(region))
        self.deletionFromGrafana = json.loads(resp.content)
        return self.deletionFromGrafana

    def deleteAnnotation(self, annotationId):
        params = dict(orgId=self.orgId)
        if self.testMode:
            return "annotations/" + str(annotationId)

        resp = self.helper.api_delete("annotations/" + str(annotationId))
        if resp.status_code != 200:
            raise Exception("Error deleting annotation " + str(annotationId))
        self.deletionFromGrafana = json.loads(resp.content)
        return self.deletionFromGrafana


    def changesList(self):
        return self.existingAnnotations.keys()

    def changeMap(self, key):
        return self.existingAnnotations.get(key, {})

    def regionIdList(self,change):
        return change.keys()

    def checkDuplicates(self):
        for dpc in self.changesList():
            _changeMap = self.changeMap(dpc)
            _regionList = self.regionIdList(_changeMap)
            d, p, h = dpc
            if len(_regionList) > 1:
                _maxRegion = max(_regionList)
                self.loggger.info("Dash %8d Panel %8d Hash %s regions found: %8d, will keep %8d" % (
                d, p, h, len(_regionList), _maxRegion))
                for _regionId in _regionList:
                    if _regionId != _maxRegion:
                        _region = _changeMap[_regionId]
                        _numberOfAnnotations = len(_region)
                        if _numberOfAnnotations == 2:
                            for _annotation in _region:
                                # self.loggger.info("About to delete annotation %s" % (json.dumps(_annotation)))
                                response = self.deleteAnnotation(_annotation['id'])
                                # self.loggger.info("Annotation deletion %d - %d response: % s" % (_regionId, _annotation['id'], response))
                            pass
                        pass
                    pass
                pass
            else:
                self.loggger.info("Dash %8d Panel %8d Hash %s region found: %8d, No Dupes" % (d, p, h, _regionList[0]))



if __name__ == '__main__':

    print("** CLEANUP START **")
    wantedOrgs = ['Staging']

    mainUtil = AnnotationsUtil(1)
    utils = [mainUtil]  # Main Org.
    orgs = mainUtil.getOrgs()
    for org in orgs:
        orgId   = org['id']
        orgName = org['name']
        if orgName in wantedOrgs:
            utils.append(AnnotationsUtil(orgId))
        pass
    pass

    for autl in utils:
        DASHES = autl.getDashboards()
        _numberOfDashboards = len(DASHES)
        autl.loggger.info("** Dashboards found for org %d: %d" % (autl.orgId, _numberOfDashboards))
        for DASH in DASHES:
            # if DASH['id'] != 33: # for debug
            #     continue
            #
            autl.loggger.info("Processing dashboard (remains %d of %d): %s" % (_numberOfDashboards, len(DASHES), json.dumps(DASH)))
            _numberOfDashboards -= 1
            _dashboardId = DASH['id']
            _panelIdList = autl.getPanelidsFromDashboard(DASH['uid'])
            for _panelId in _panelIdList:
                # if _panelId != 1:  # for debug
                #     continue
                autl.loggger.info("** Processing Panel %d" % (_panelId))
                _dashAnnotations = autl.getAnnotationsOnDashboardPanel(dashboardId=_dashboardId, panelId=_panelId)
                _numberOfAnnotationsReturned = len(_dashAnnotations)

                autl.loggger.info("** Ann returned %d" % (_numberOfAnnotationsReturned))

                autl.setLimitStatus(state=(_numberOfAnnotationsReturned == autl.limit))
                if _numberOfAnnotationsReturned > 0:
                    _result = autl.loadAnnotationsReturnedFromGrafana(_dashAnnotations)
                    autl.checkDuplicates()
                else:
                    autl.loggger.info("** No annotations for dashboard %d %s %s Panel %d" % (_dashboardId, DASH['uid'], DASH['title'], _panelId))
                autl.reset()
            pass
        pass
    pass




    print("**END**")
