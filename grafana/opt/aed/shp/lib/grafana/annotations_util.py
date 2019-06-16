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

sys.path.append('/opt/aed/shp/lib')
sys.path.append('/opt/aed/shp/lib/grafana')

import shputil
from helper import Helper


class AnnotationsUtil():


    def __init__(self, org_id):
        self.testMode = False
        self.org_id = org_id
        self.existingAnnotations = dict() # indexed by (dashboardId, panelId, hash)
        self.helper = Helper(org_id)
        # self.load_all()

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

    def addAnnotationToExisting(self, grafanaAnnotation):
        _text = grafanaAnnotation.get('text',None)
        if _text:
            _hash = self.parseSysId(_text)
            _key = (grafanaAnnotation['dashboardId'], grafanaAnnotation['panelId'], _hash)


            self.existingAnnotations.setdefault(_key,dict())

            _regionId = grafanaAnnotation['regionId']
            _changeOnPanel = self.existingAnnotations[_key]

            _changeOnPanel.setdefault(_regionId,[])
            #_changeOnPanel[_regionId].append(grafanaAnnotation)

            _annotationSubset = dict(id=None, time=None, dashboardId=None, panelId=None, regionId=None)
            dictSetValues = lambda x, y: dict([(i, x[i]) for i in x if i in set(y)])
            _annotationSubset = dictSetValues(grafanaAnnotation, set(_annotationSubset))

            _change = self.parseChange(_text)
            _annotationSubset['change'] = _change
            if len(_changeOnPanel[_regionId]) > 1 and _annotationSubset['id'] > _changeOnPanel[_regionId][0]['id']:
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
            _annotation1 = json.dumps(_region[0])
            _annotation2 = json.dumps(_region[1])

            print("# Dash %8d Panel %8d Hash %-32s Region %8d A1: %s A2: %s" %
                    ( _dashboardId, _panelId, hash, _regionId,
                      _annotation1, _annotation2
                    )
                  )

    def printAllExistingAnnotations(self):

        for _key in self.getExistingChangesOnPanelFromDashboard():
            self.printExistingAnnotation(_key)


    def loadAnnotationsReturnedFromGrafana(self, annotations):
        for _annotation in annotations:
            self.addAnnotationToExisting(_annotation)
        return True


    def testMyself(self):
        self.testMode = True
        self.loadAnnotationsReturnedFromGrafana(self.getExampleOfGrafanaAnnotations())
        return True


    def getDashboards(self, *args, **kwargs):
        resp = self.helper.api_get_with_params("search", {'type': 'dash-db'})
        dashboards = json.loads(resp.content)
        return dashboards


    def getAnnotationsOnDashboard(self, *args, **kwargs):
        params = dict(type='annotation', dashboardId=kwargs.get('dashboardId',0), limit=kwargs.get('limit',15000))
        #params.update(kwargs)

        resp = self.helper.api_get_with_params("annotations", params)
        self.annotationsFromGrafana = json.loads(resp.content)
        return self.annotationsFromGrafana


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


    def getExampleOfGrafanaAnnotations(self):

        example42 = [{"id":8530894,"alertId":0,"alertName":"","dashboardId":42,"panelId":1,"userId":0,"newState":"","prevState":"","created":1560517400216,"updated":1560517400216,"time":1560517608000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=96ea4f1d13c2b740b8a179566144b0f8'\u003eCHG0469048\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8530893,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8530896,"alertId":0,"alertName":"","dashboardId":42,"panelId":2,"userId":0,"newState":"","prevState":"","created":1560517400254,"updated":1560517400254,"time":1560517608000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=96ea4f1d13c2b740b8a179566144b0f8'\u003eCHG0469048\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8530895,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8530898,"alertId":0,"alertName":"","dashboardId":42,"panelId":3,"userId":0,"newState":"","prevState":"","created":1560517400293,"updated":1560517400293,"time":1560517608000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=96ea4f1d13c2b740b8a179566144b0f8'\u003eCHG0469048\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8530897,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8530900,"alertId":0,"alertName":"","dashboardId":42,"panelId":3000,"userId":0,"newState":"","prevState":"","created":1560517400332,"updated":1560517400332,"time":1560517608000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=96ea4f1d13c2b740b8a179566144b0f8'\u003eCHG0469048\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8530899,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8530893,"alertId":0,"alertName":"","dashboardId":42,"panelId":1,"userId":0,"newState":"","prevState":"","created":1560517400206,"updated":1560517400211,"time":1560516708000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=96ea4f1d13c2b740b8a179566144b0f8'\u003eCHG0469048\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8530893,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8530895,"alertId":0,"alertName":"","dashboardId":42,"panelId":2,"userId":0,"newState":"","prevState":"","created":1560517400245,"updated":1560517400250,"time":1560516708000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=96ea4f1d13c2b740b8a179566144b0f8'\u003eCHG0469048\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8530895,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8530897,"alertId":0,"alertName":"","dashboardId":42,"panelId":3,"userId":0,"newState":"","prevState":"","created":1560517400283,"updated":1560517400288,"time":1560516708000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=96ea4f1d13c2b740b8a179566144b0f8'\u003eCHG0469048\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8530897,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8530899,"alertId":0,"alertName":"","dashboardId":42,"panelId":3000,"userId":0,"newState":"","prevState":"","created":1560517400322,"updated":1560517400327,"time":1560516708000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=96ea4f1d13c2b740b8a179566144b0f8'\u003eCHG0469048\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8530899,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8523212,"alertId":0,"alertName":"","dashboardId":42,"panelId":1,"userId":0,"newState":"","prevState":"","created":1560510199499,"updated":1560510199499,"time":1560510557000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=34007ad91302b740b8a179566144b083'\u003eCHG0469047\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8523211,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8523214,"alertId":0,"alertName":"","dashboardId":42,"panelId":2,"userId":0,"newState":"","prevState":"","created":1560510199537,"updated":1560510199537,"time":1560510557000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=34007ad91302b740b8a179566144b083'\u003eCHG0469047\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8523213,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8523216,"alertId":0,"alertName":"","dashboardId":42,"panelId":3,"userId":0,"newState":"","prevState":"","created":1560510199578,"updated":1560510199578,"time":1560510557000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=34007ad91302b740b8a179566144b083'\u003eCHG0469047\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8523215,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8523218,"alertId":0,"alertName":"","dashboardId":42,"panelId":3000,"userId":0,"newState":"","prevState":"","created":1560510199618,"updated":1560510199618,"time":1560510557000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=34007ad91302b740b8a179566144b083'\u003eCHG0469047\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8523217,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8522798,"alertId":0,"alertName":"","dashboardId":42,"panelId":1,"userId":0,"newState":"","prevState":"","created":1560509598148,"updated":1560509598148,"time":1560510016000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=6cfdea951302b740b8a179566144b0cb'\u003eCHG0469046\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8522797,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8522800,"alertId":0,"alertName":"","dashboardId":42,"panelId":2,"userId":0,"newState":"","prevState":"","created":1560509598187,"updated":1560509598187,"time":1560510016000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=6cfdea951302b740b8a179566144b0cb'\u003eCHG0469046\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8522799,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8522802,"alertId":0,"alertName":"","dashboardId":42,"panelId":3,"userId":0,"newState":"","prevState":"","created":1560509598227,"updated":1560509598227,"time":1560510016000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=6cfdea951302b740b8a179566144b0cb'\u003eCHG0469046\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8522801,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8522804,"alertId":0,"alertName":"","dashboardId":42,"panelId":3000,"userId":0,"newState":"","prevState":"","created":1560509598266,"updated":1560509598266,"time":1560510016000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=6cfdea951302b740b8a179566144b0cb'\u003eCHG0469046\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8522803,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8523211,"alertId":0,"alertName":"","dashboardId":42,"panelId":1,"userId":0,"newState":"","prevState":"","created":1560510199490,"updated":1560510199495,"time":1560509657000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=34007ad91302b740b8a179566144b083'\u003eCHG0469047\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8523211,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8523213,"alertId":0,"alertName":"","dashboardId":42,"panelId":2,"userId":0,"newState":"","prevState":"","created":1560510199528,"updated":1560510199533,"time":1560509657000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=34007ad91302b740b8a179566144b083'\u003eCHG0469047\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8523213,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8523215,"alertId":0,"alertName":"","dashboardId":42,"panelId":3,"userId":0,"newState":"","prevState":"","created":1560510199567,"updated":1560510199573,"time":1560509657000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=34007ad91302b740b8a179566144b083'\u003eCHG0469047\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8523215,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8523217,"alertId":0,"alertName":"","dashboardId":42,"panelId":3000,"userId":0,"newState":"","prevState":"","created":1560510199607,"updated":1560510199613,"time":1560509657000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=34007ad91302b740b8a179566144b083'\u003eCHG0469047\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8523217,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8522797,"alertId":0,"alertName":"","dashboardId":42,"panelId":1,"userId":0,"newState":"","prevState":"","created":1560509598140,"updated":1560509598144,"time":1560509116000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=6cfdea951302b740b8a179566144b0cb'\u003eCHG0469046\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8522797,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8522799,"alertId":0,"alertName":"","dashboardId":42,"panelId":2,"userId":0,"newState":"","prevState":"","created":1560509598177,"updated":1560509598182,"time":1560509116000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=6cfdea951302b740b8a179566144b0cb'\u003eCHG0469046\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8522799,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8522801,"alertId":0,"alertName":"","dashboardId":42,"panelId":3,"userId":0,"newState":"","prevState":"","created":1560509598216,"updated":1560509598222,"time":1560509116000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=6cfdea951302b740b8a179566144b0cb'\u003eCHG0469046\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8522801,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8522803,"alertId":0,"alertName":"","dashboardId":42,"panelId":3000,"userId":0,"newState":"","prevState":"","created":1560509598256,"updated":1560509598261,"time":1560509116000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=6cfdea951302b740b8a179566144b0cb'\u003eCHG0469046\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"","regionId":8522803,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1447,"alertId":0,"alertName":"","dashboardId":42,"panelId":1,"userId":0,"newState":"","prevState":"","created":1558537416908,"updated":1558537416908,"time":1558079213000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=5b75b535dba8bfc0295870d9af9619cb'\u003eCHG0447051\u003c/a\u003e: HP OTS/WIN and DPLS Windows – Q2 2019  + BIOS/FIRMWARE   + SEP Upgrade  + MPIO checks  -EMGHWP1215 / EMGHWP1216 /EMGHWP1217 / EMGHWP1218 -PROD-CLUSTER","regionId":1446,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1453,"alertId":0,"alertName":"","dashboardId":42,"panelId":2,"userId":0,"newState":"","prevState":"","created":1558537417089,"updated":1558537417089,"time":1558079213000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=5b75b535dba8bfc0295870d9af9619cb'\u003eCHG0447051\u003c/a\u003e: HP OTS/WIN and DPLS Windows – Q2 2019  + BIOS/FIRMWARE   + SEP Upgrade  + MPIO checks  -EMGHWP1215 / EMGHWP1216 /EMGHWP1217 / EMGHWP1218 -PROD-CLUSTER","regionId":1452,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1459,"alertId":0,"alertName":"","dashboardId":42,"panelId":3,"userId":0,"newState":"","prevState":"","created":1558537417271,"updated":1558537417271,"time":1558079213000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=5b75b535dba8bfc0295870d9af9619cb'\u003eCHG0447051\u003c/a\u003e: HP OTS/WIN and DPLS Windows – Q2 2019  + BIOS/FIRMWARE   + SEP Upgrade  + MPIO checks  -EMGHWP1215 / EMGHWP1216 /EMGHWP1217 / EMGHWP1218 -PROD-CLUSTER","regionId":1458,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8511457,"alertId":0,"alertName":"","dashboardId":42,"panelId":3000,"userId":0,"newState":"","prevState":"","created":1560492798609,"updated":1560492798609,"time":1558079213000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=5b75b535dba8bfc0295870d9af9619cb'\u003eCHG0447051\u003c/a\u003e: HP OTS/WIN and DPLS Windows – Q2 2019  + BIOS/FIRMWARE   + SEP Upgrade  + MPIO checks  -EMGHWP1215 / EMGHWP1216 /EMGHWP1217 / EMGHWP1218 -PROD-CLUSTER","regionId":8511456,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1446,"alertId":0,"alertName":"","dashboardId":42,"panelId":1,"userId":0,"newState":"","prevState":"","created":1558537416888,"updated":1558537416898,"time":1558056894000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=5b75b535dba8bfc0295870d9af9619cb'\u003eCHG0447051\u003c/a\u003e: HP OTS/WIN and DPLS Windows – Q2 2019  + BIOS/FIRMWARE   + SEP Upgrade  + MPIO checks  -EMGHWP1215 / EMGHWP1216 /EMGHWP1217 / EMGHWP1218 -PROD-CLUSTER","regionId":1446,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1452,"alertId":0,"alertName":"","dashboardId":42,"panelId":2,"userId":0,"newState":"","prevState":"","created":1558537417069,"updated":1558537417079,"time":1558056894000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=5b75b535dba8bfc0295870d9af9619cb'\u003eCHG0447051\u003c/a\u003e: HP OTS/WIN and DPLS Windows – Q2 2019  + BIOS/FIRMWARE   + SEP Upgrade  + MPIO checks  -EMGHWP1215 / EMGHWP1216 /EMGHWP1217 / EMGHWP1218 -PROD-CLUSTER","regionId":1452,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1458,"alertId":0,"alertName":"","dashboardId":42,"panelId":3,"userId":0,"newState":"","prevState":"","created":1558537417251,"updated":1558537417261,"time":1558056894000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=5b75b535dba8bfc0295870d9af9619cb'\u003eCHG0447051\u003c/a\u003e: HP OTS/WIN and DPLS Windows – Q2 2019  + BIOS/FIRMWARE   + SEP Upgrade  + MPIO checks  -EMGHWP1215 / EMGHWP1216 /EMGHWP1217 / EMGHWP1218 -PROD-CLUSTER","regionId":1458,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":8511456,"alertId":0,"alertName":"","dashboardId":42,"panelId":3000,"userId":0,"newState":"","prevState":"","created":1560492798599,"updated":1560492798605,"time":1558056894000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=5b75b535dba8bfc0295870d9af9619cb'\u003eCHG0447051\u003c/a\u003e: HP OTS/WIN and DPLS Windows – Q2 2019  + BIOS/FIRMWARE   + SEP Upgrade  + MPIO checks  -EMGHWP1215 / EMGHWP1216 /EMGHWP1217 / EMGHWP1218 -PROD-CLUSTER","regionId":8511456,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1451,"alertId":0,"alertName":"","dashboardId":42,"panelId":1,"userId":0,"newState":"","prevState":"","created":1558537417029,"updated":1558537417029,"time":1557823895000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=eda17f0adbe03b000f9377e9af961994'\u003eCHG0447773\u003c/a\u003e: HP OTS/WIN and DPLS Windows – Q2 2019   + BIOS/FIRMWARE + SEP +  MPIO Checks - EMGHWP1793 / EMGHWP1794 - PROD(Cluster)DBPE-SQL","regionId":1450,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1457,"alertId":0,"alertName":"","dashboardId":42,"panelId":2,"userId":0,"newState":"","prevState":"","created":1558537417210,"updated":1558537417210,"time":1557823895000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=eda17f0adbe03b000f9377e9af961994'\u003eCHG0447773\u003c/a\u003e: HP OTS/WIN and DPLS Windows – Q2 2019   + BIOS/FIRMWARE + SEP +  MPIO Checks - EMGHWP1793 / EMGHWP1794 - PROD(Cluster)DBPE-SQL","regionId":1456,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1463,"alertId":0,"alertName":"","dashboardId":42,"panelId":3,"userId":0,"newState":"","prevState":"","created":1558537417390,"updated":1558537417390,"time":1557823895000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=eda17f0adbe03b000f9377e9af961994'\u003eCHG0447773\u003c/a\u003e: HP OTS/WIN and DPLS Windows – Q2 2019   + BIOS/FIRMWARE + SEP +  MPIO Checks - EMGHWP1793 / EMGHWP1794 - PROD(Cluster)DBPE-SQL","regionId":1462,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1450,"alertId":0,"alertName":"","dashboardId":42,"panelId":1,"userId":0,"newState":"","prevState":"","created":1558537417009,"updated":1558537417019,"time":1557799146000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=eda17f0adbe03b000f9377e9af961994'\u003eCHG0447773\u003c/a\u003e: HP OTS/WIN and DPLS Windows – Q2 2019   + BIOS/FIRMWARE + SEP +  MPIO Checks - EMGHWP1793 / EMGHWP1794 - PROD(Cluster)DBPE-SQL","regionId":1450,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1456,"alertId":0,"alertName":"","dashboardId":42,"panelId":2,"userId":0,"newState":"","prevState":"","created":1558537417190,"updated":1558537417200,"time":1557799146000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=eda17f0adbe03b000f9377e9af961994'\u003eCHG0447773\u003c/a\u003e: HP OTS/WIN and DPLS Windows – Q2 2019   + BIOS/FIRMWARE + SEP +  MPIO Checks - EMGHWP1793 / EMGHWP1794 - PROD(Cluster)DBPE-SQL","regionId":1456,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1462,"alertId":0,"alertName":"","dashboardId":42,"panelId":3,"userId":0,"newState":"","prevState":"","created":1558537417371,"updated":1558537417381,"time":1557799146000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=eda17f0adbe03b000f9377e9af961994'\u003eCHG0447773\u003c/a\u003e: HP OTS/WIN and DPLS Windows – Q2 2019   + BIOS/FIRMWARE + SEP +  MPIO Checks - EMGHWP1793 / EMGHWP1794 - PROD(Cluster)DBPE-SQL","regionId":1462,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1449,"alertId":0,"alertName":"","dashboardId":42,"panelId":1,"userId":0,"newState":"","prevState":"","created":1558537416969,"updated":1558537416969,"time":1555995032000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=c690b5dedb787f48295870d9af96190f'\u003eCHG0453861\u003c/a\u003e: Import Renewal SSL(s) for travelbank.prod.sabre.com  - TCVDMZ02P/S","regionId":1448,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1455,"alertId":0,"alertName":"","dashboardId":42,"panelId":2,"userId":0,"newState":"","prevState":"","created":1558537417149,"updated":1558537417149,"time":1555995032000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=c690b5dedb787f48295870d9af96190f'\u003eCHG0453861\u003c/a\u003e: Import Renewal SSL(s) for travelbank.prod.sabre.com  - TCVDMZ02P/S","regionId":1454,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1461,"alertId":0,"alertName":"","dashboardId":42,"panelId":3,"userId":0,"newState":"","prevState":"","created":1558537417331,"updated":1558537417331,"time":1555995032000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=c690b5dedb787f48295870d9af96190f'\u003eCHG0453861\u003c/a\u003e: Import Renewal SSL(s) for travelbank.prod.sabre.com  - TCVDMZ02P/S","regionId":1460,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1448,"alertId":0,"alertName":"","dashboardId":42,"panelId":1,"userId":0,"newState":"","prevState":"","created":1558537416949,"updated":1558537416959,"time":1555989719000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=c690b5dedb787f48295870d9af96190f'\u003eCHG0453861\u003c/a\u003e: Import Renewal SSL(s) for travelbank.prod.sabre.com  - TCVDMZ02P/S","regionId":1448,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1454,"alertId":0,"alertName":"","dashboardId":42,"panelId":2,"userId":0,"newState":"","prevState":"","created":1558537417129,"updated":1558537417139,"time":1555989719000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=c690b5dedb787f48295870d9af96190f'\u003eCHG0453861\u003c/a\u003e: Import Renewal SSL(s) for travelbank.prod.sabre.com  - TCVDMZ02P/S","regionId":1454,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}},{"id":1460,"alertId":0,"alertName":"","dashboardId":42,"panelId":3,"userId":0,"newState":"","prevState":"","created":1558537417311,"updated":1558537417321,"time":1555989719000,"text":"\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=c690b5dedb787f48295870d9af96190f'\u003eCHG0453861\u003c/a\u003e: Import Renewal SSL(s) for travelbank.prod.sabre.com  - TCVDMZ02P/S","regionId":1460,"tags":[],"login":"admin","email":"admin@localhost","avatarUrl":"/grafana/avatar/46d229b033af06a191ff2267bca9ae56","data":{}}]
        return example42

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
                print("Dash %8d Panel %8d Hash %s regions found: %8d, will keep %8d" % (
                d, p, h, len(_regionList), _maxRegion))
                for _regionId in _regionList:
                    if _regionId != _maxRegion:
                        _region = _changeMap[_regionId]
                        for _annotation in _region:
                            print("About to delete annotation %s" % (json.dumps(_annotation)))
                            response = self.deleteAnnotation(_annotation['id'])
                        pass
                    pass
                pass
            else:
                print("Dash %8d Panel %8d Hash %s region found: %8d, No Dupes" % (d, p, h, _regionList[0]))


if __name__ == '__main__':

    print("**START**")

    orgId = 1
    autl = AnnotationsUtil(orgId)

    # autil.testMyself()

    DASHES = autl.getDashboards()

    for DASH in DASHES:
        _dashboardId = DASH['id']
        _dashAnnotations = autl.getAnnotationsOnDashboard(dashboardId=_dashboardId, limit=20000)
        _result = autl.loadAnnotationsReturnedFromGrafana(_dashAnnotations)

        autl.printAllExistingAnnotations()
        autl.checkDuplicates()

    print("**END**")