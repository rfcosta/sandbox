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

    exampleFromGrafana = [
        {"id": 14031586, "alertId": 0, "alertName": "", "dashboardId": 25, "panelId": 3000, "userId": 0, "newState": "",
         "prevState": "", "created": 1560517402729, "updated": 1560517402729, "time": 1560517608000,
         "text": "\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=96ea4f1d13c2b740b8a179566144b0f8'\u003eCHG0469048\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"",
         "regionId": 14031585, "tags": [], "login": "admin", "email": "admin@localhost",
         "avatarUrl": "/grafana/avatar/46d229b033af06a191ff2267bca9ae56", "data": {}},
        {"id": 14031584, "alertId": 0, "alertName": "", "dashboardId": 25, "panelId": 3, "userId": 0, "newState": "",
         "prevState": "", "created": 1560517402664, "updated": 1560517402664, "time": 1560517608000,
         "text": "\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=96ea4f1d13c2b740b8a179566144b0f8'\u003eCHG0469048\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"",
         "regionId": 14031583, "tags": [], "login": "admin", "email": "admin@localhost",
         "avatarUrl": "/grafana/avatar/46d229b033af06a191ff2267bca9ae56", "data": {}},
        {"id": 14031582, "alertId": 0, "alertName": "", "dashboardId": 25, "panelId": 2, "userId": 0, "newState": "",
         "prevState": "", "created": 1560517402515, "updated": 1560517402515, "time": 1560517608000,
         "text": "\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=96ea4f1d13c2b740b8a179566144b0f8'\u003eCHG0469048\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"",
         "regionId": 14031581, "tags": [], "login": "admin", "email": "admin@localhost",
         "avatarUrl": "/grafana/avatar/46d229b033af06a191ff2267bca9ae56", "data": {}},
        {"id": 14031580, "alertId": 0, "alertName": "", "dashboardId": 25, "panelId": 1, "userId": 0, "newState": "",
         "prevState": "", "created": 1560517402448, "updated": 1560517402448, "time": 1560517608000,
         "text": "\u003ca target=\"_blank\" href='https://sabretest.service-now.com/nav_to.do?uri=change_request.do?sys_id=96ea4f1d13c2b740b8a179566144b0f8'\u003eCHG0469048\u003c/a\u003e: SHP: Update graph panel for \"CENTIVA\" of \"B6_Error Count\"",
         "regionId": 14031579, "tags": [], "login": "admin", "email": "admin@localhost",
         "avatarUrl": "/grafana/avatar/46d229b033af06a191ff2267bca9ae56", "data": {}}
    ]

    def __init__(self, org_id):
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
    def parseChange(self,_annotation):
        _change = ''
        _XCHANG = re.compile('https[:][/][/]\S+\?sys_id=[0123456789abcdef]{32}..CHG(\d+)')
        _text = _annotation.get('text')
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
        _hash = self.parseSysid(grafanaAnnotation['text'])
        _key = (grafanaAnnotation['dashboardId'], grafanaAnnotation['panelId'], _hash)

        self.existingAnnotations.setdefault(_key,dict())

        _regionId = grafanaAnnotation['regionId']
        self.existingAnnotations[_key].setdefault(_regionId,[])

        self.existingAnnotations[_key][_regionId].append(grafanaAnnotation)

        return self.existingAnnotations[_key][_regionId]

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


    def loadAnnotationsFromGrafana(self, annotations):
        for _annotation in annotations:
            self.addAnnotationToExisting(_annotation)

    def setTestPayload(self, payload):
        self.exampleFromGrafana = payload

    def testMyLoad(self):
        self.loadAnnotationsFromGrafana(self.exampleFromGrafana)

    def getDashboards(self, *args, **kwargs):
        resp = self.helper.api_get_with_params("search", {'type': 'dash-db'})
        dashboards = json.loads(resp.content)
        return dashboards

    def getAnnotationsOnDashboard(self, *args, **kwargs):
        params = dict(type='annotation', dashboardId=kwargs.get('dashboardId',0), limit=kwargs.get('limit',500))
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



