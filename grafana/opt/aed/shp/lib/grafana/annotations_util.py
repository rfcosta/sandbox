#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import json
import datetime
import re
import os

import logging
from logging import getLogger, DEBUG, INFO, WARNING, ERROR

sys.path.append('/opt/aed/shp/lib')
sys.path.append('/opt/aed/shp/lib/grafana')

import shputil
from helper import Helper


class AnnotationsUtil():
    LOG_LEVEL_DEFAULT = DEBUG
    NAME_DEFAULT = __name__

    def __init__(self, *args, **kwargs):

        _myname = kwargs.get('myname', self.NAME_DEFAULT)
        _loglevel = kwargs.get('loglevel', self.LOG_LEVEL_DEFAULT)
        _panelids = kwargs.get('panelids', True)
        _orgId = kwargs.get('orgId', 1)

        self.helper = Helper(_orgId)
        self.orgId = _orgId
        self.reset()
        _logger = getLogger(_myname + str(self.orgId))

        if _logger.handlers.__len__() == 0:
            _logger.propagate = 0
            _formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s %(funcName)s:%(lineno)d: %(message)s')
            _console_handler = logging.StreamHandler()
            _console_handler.setFormatter(_formatter)
            _logger.addHandler(_console_handler)

        self.loggger = _logger
        self.loggger.setLevel(_loglevel)

        self.loggger.debug("Util init start for org %d" % (self.orgId))
        self.CONFIG = shputil.get_config()
        self.CONFIG_FILE_NAME = self.CONFIG.get('service_configuration_file')
        self.CHANGE_FILE_NAME = self.CONFIG.get('change_configuration_file')
        self.dashboardList = self.getDashboards(panelids=_panelids)

        _logger.debug("Util init end for org %d, %d dashboards found" % (self.orgId, len(self.dashboardList)))

    def reset(self):
        self.limit = 20000
        self.limitReached = True
        self.testMode = False
        self.existingAnnotations = dict()  # indexed by (dashboardId, panelId, hash)

    def setLimitStatus(self, state=True):
        self.limitReached = state
        if state:
            self.loggger.warn("** Limit Reached Status set to " + str(self.limitReached))

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
            raise err
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
        # _text = _annotation.get('text')
        if _text:
            _tokens = _XCHANG.findall(_text)
            if _tokens.__len__() > 0:
                _change = _tokens[0]
        return 'CHG' + _change

    @staticmethod
    def regionRequest(*args, **kwargs):

        _regionRequest = dict(
            dashboardId=kwargs.get("dashboardId"),
            panelId=kwargs.get("panelId"),
            time=kwargs.get("time"),
            timeEnd=kwargs.get("timeEnd"),
            isRegion=True,
            text=kwargs.get("text"),
            title=kwargs.get("title", ''),
            tags=kwargs.get("tags", [])
        )

        for p in ['dashboardId', 'panelId', 'time', 'timeEnd', 'text', 'isRegion']:
            if not _regionRequest[p]:
                raise Exception("#Annotations.regionRequest: Missing %s" % (p))

        return _regionRequest

    def addAnnotationToExisting(self, grafanaAnnotation, dupes=False):
        _text = grafanaAnnotation.get('text', None)
        if _text:
            _hash = self.parseSysId(_text)
            _key = (grafanaAnnotation['dashboardId'], grafanaAnnotation['panelId'], _hash)

            self.existingAnnotations.setdefault(_key, dict())

            _regionId = grafanaAnnotation.get('regionId',-1)  # New Version of Grafana doesn't have regionId
            _annotationKey = _regionId if _regionId > 0 else grafanaAnnotation.get('id',-1)

            _changeOnPanel = self.existingAnnotations[_key]

            _ignore = False
            _changeOnPanel.setdefault(_annotationKey, [])

            # only need to del region dupes it there are regions.
            # There's no regionId on new Grafana so duplicates are naturaly overriden
            # since the hashkey _annotationKey is the unique annotation Id
            if _regionId > 0 and not dupes:
                _latestRegionId = max(_changeOnPanel.keys())

                for _rId in list(_changeOnPanel.keys()):
                    if _rId != _latestRegionId:
                        del _changeOnPanel[_rId]
                    pass
                pass
            pass

            if _annotationKey in _changeOnPanel:
                _annotationSubset = dict(id=None, time=None, timeEnd=None, dashboardId=None, panelId=None, regionId=None, text=None)
                dictSetValues = lambda x, y: dict([(i, x[i]) for i in x if i in set(y)])
                _annotationSubset = dictSetValues(grafanaAnnotation, set(_annotationSubset))

                _change = self.parseChange(_text)
                _annotationSubset['change'] = _change

                if len(_changeOnPanel[_annotationKey]) > 0 and _annotationSubset['id'] > _changeOnPanel[_annotationKey][0]['id']:
                    _changeOnPanel[_annotationKey].append(_annotationSubset)
                else:
                    _changeOnPanel[_annotationKey].insert(0, _annotationSubset)
                pass

                return _changeOnPanel[_annotationKey]
            pass

        return False

    def getExistingChangesOnPanelFromDashboard(self):
        return list(self.existingAnnotations.keys())

    def printExistingAnnotation(self, key):
        _dashboardId, _panelId, hash = key

        for _regionId in list(self.existingAnnotations[key].keys()):
            _region = self.existingAnnotations[key][_regionId]
            _numberOfAnnotations = len(_region)
            if _numberOfAnnotations == 2:
                _annotation1 = json.dumps(_region[0])
                _annotation2 = json.dumps(_region[1])

                self.loggger.info("# Dash %8d Panel %8d Hash %-32s Region %8d A1: %s A2: %s" %
                                  (_dashboardId, _panelId, hash, _regionId,
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

    def getPanelidsFromDashboard(self, uid):
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
        if kwargs.get("panelids", True):
            for dashboard in dashboards:
                dashboard['panelids'] = self.getPanelidsFromDashboard(dashboard['uid'])
        return dashboards

    def getAnnotationsOnDashboard(self, *args, **kwargs):
        _annotationsFromGrafana = []
        if kwargs.get('dashboardId'):
            params = dict(type='annotation',
                          dashboardId=kwargs.get('dashboardId', 0),
                          limit=kwargs.get('limit', self.limit)
                          )

            resp = self.helper.api_get_with_params("annotations", params)
            _annotationsFromGrafana = json.loads(resp.content)
        return _annotationsFromGrafana

    def getAnnotationsOnDashboardPanel(self, *args, **kwargs):
        _annotationsFromGrafana = []
        if kwargs.get('dashboardId') and kwargs.get('panelId'):
            params = dict(type='annotation',
                          dashboardId=kwargs.get('dashboardId', 0),
                          panelId=kwargs.get('panelId', 0),
                          limit=kwargs.get('limit', self.limit)
                          )

            resp = self.helper.api_get_with_params("annotations", params)
            _annotationsFromGrafana = json.loads(resp.content)
        return _annotationsFromGrafana

    def deleteAnnotationByRegion(self, region):
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

    def createAnnotationPair(self, annotationRequest, **kwargs):

        returnText = ''
        try:
            _createResponse = self.helper.api_post_with_data('annotations', annotationRequest)
            self.loggger.debug("#createAnnotationPair> add Response = " + _createResponse.text)
            returnText = str(_createResponse.text)
        except Exception as E:
            self.loggger.warn("#createAnnotationPair> Exception: " + str(E.message))
            returnText = str(E.message)
            pass

        return returnText

    def updateAnnotationPair(self, annotationRequest, region, **kwargs):

        returnText = ''
        annotationId = region[0]['id']
        try:
            aupdatedata = dict(text=annotationRequest['text'],
                               time=annotationRequest['time'],
                               isRegion=annotationRequest['isRegion'],
                               timeEnd=annotationRequest['timeEnd'],
                               tags=annotationRequest['tags']
                               )
            _updateResponse = self.helper.api_put_with_data('annotations/' + str(annotationId), aupdatedata)
            returnText = str(_updateResponse.text)

        except Exception as E:
            self.loggger.warn("#updateAnnotationPair> Exception: " + str(E.message))
            returnText = str(E.message)
            pass

        return returnText

    def changesList(self):
        return list(self.existingAnnotations.keys())

    def changeMap(self, key):
        return self.existingAnnotations.get(key, {})

    def regionIdList(self, change):
        return list(change.keys())

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

    def getConfigFiles(self, *args, **kwargs):
        if not os.path.exists(self.CONFIG_FILE_NAME):
            os.system("/opt/aed/shp/bin/download_service_configurations.py")
        self.servicesInfo = self.LoadFile(self.CONFIG_FILE_NAME)
        if not os.path.exists(self.CHANGE_FILE_NAME):
            os.system("/opt/aed/shp/bin/download_change_configurations.py")
        self.changesInfo = self.LoadFile(self.CHANGE_FILE_NAME)
        return {"changesInfo": self.changesInfo, "servicesInfo": self.servicesInfo}

    def indexDashboards(self, *args, **kwargs):
        # Build table of dashboardsID per UUID
        self.dashboardIndex = {"dashboards": self.dashboardList}

        for _dash in self.dashboardList:
            _uid = _dash['uid']
            _id = _dash['id']
            _panels = _dash['panelids']
            _dictEntry = {"uid": _uid, "id": _id, "panels": _panels}
            self.dashboardIndex[_uid] = _dictEntry
            self.dashboardIndex[_id] = _dictEntry

        return self.dashboardIndex

    @staticmethod
    def annotationRequest(*args, **kwargs):

        _dashboardId = kwargs.get("DASHBOARD")
        _panelId = kwargs.get("PANEL")
        _time = kwargs.get("TIME")
        _timeEnd = kwargs.get("ENDTIME")
        _isRegion = True
        if not _timeEnd:
            _isRegion = False

        _text = kwargs.get("TEXT")
        _title = kwargs.get("TITLE")
        _tags = kwargs.get("TAGS")

        if not _dashboardId:
            raise Exception("#annotationRequest: Missing DASHBOARD=")
        if not _panelId:
            raise Exception("#annotationRequest: Missing PANEL=")
        if not _time:
            raise Exception("#annotationRequest: Missing TIME=")
        if not _text:
            raise Exception("#annotationRequest: Missing TEXT=")
        if not _tags:
            _tags = []

        if not _title:
            _title = ''

        _annotationReq = {
            "dashboardId": _dashboardId,
            "panelId": _panelId,
            "time": _time,  # int(change['start_datetime']),
            "isRegion": _isRegion,
            "timeEnd": _timeEnd,  # int(change['end_datetime']),
            "tags": _tags,  # [change['number']],
            "title": _title,  # change['number'] + " " + change['short_description'],
            "text": _text
        }

        return _annotationReq

    def makeAnnotationsRequestsForServices(self, *args, **kwargs):
        #
        # Start matching changes with panels from change's cmdb_ci
        # and create annotations requests
        #

        annotationsReqs = {}  # By Dashboard ID

        allConfigInfo = self.getConfigFiles()
        changesInfo = allConfigInfo['changesInfo']
        servicesInfo = allConfigInfo['servicesInfo']
        dashboardDict = self.indexDashboards()

        apiVersionNumber = changesInfo['result'].get('thisapiversion', 1)
        newApiVersion = (apiVersionNumber > 1)

        changedServicesList = []
        if newApiVersion:
            changedServicesList = [changesInfo['result']['services'][service]['name']
                                   for service in
                                   list(changesInfo['result']['services'].keys())]
        else:
            changedServicesList = [service for service in list(changesInfo['result']['services'].keys())]

        self.loggger.debug("#Changed Services List: " + str(changedServicesList))

        for service in changedServicesList:
            serviceEntry = servicesInfo['result']['services'].get(service)

            if serviceEntry:
                serviceUID = serviceEntry['uid']
                # Look for the service UID on dashboards
                if serviceUID in dashboardDict:
                    dashboardID = dashboardDict[serviceUID]['id']
                else:
                    dashboardID = 0

                if dashboardID > 0:
                    annotationsReqs.setdefault(dashboardID, [])

                    _panels = dashboardDict[serviceUID]['panels']
                    self.loggger.debug("#Panels List: " + str(_panels))
                    for _panel_id in _panels:
                        # _panel_id = _panel['id']
                        changes = []
                        if newApiVersion:
                            changes = changesInfo['result']['services'][serviceUID]['changes']
                        else:
                            changes = changesInfo['result']['services'][service]['changes']

                        for change in changes:
                            # Version 1 change entry is the change object
                            if newApiVersion:
                                _changenumber = str(change)
                                change = changesInfo['result']['changes'][change]
                                change['number'] = _changenumber

                            _annotation_start = int(str(int(change['start_datetime'])) + '000')
                            _annotation_end = int(str(int(change['end_datetime'])) + '000')

                            _work_start_datetime = int(change.get('work_start_datetime'))
                            _work_end_datetime = int(change.get('work_end_datetime'))

                            if _work_start_datetime > 0:
                                _annotation_start = int(str(_work_start_datetime) + '000')

                            if _work_end_datetime > 0:
                                _annotation_end = int(str(_work_end_datetime) + '000')

                            _annotationReq = self.annotationRequest(
                                DASHBOARD=dashboardID,
                                PANEL=_panel_id,
                                TIME=_annotation_start,
                                ENDTIME=_annotation_end,
                                TAGS=[],  # [change['number']],
                                TEXT="<a target=\"_blank\" href='https://" + changesInfo['result']['instancename'] +
                                     ".service-now.com/nav_to.do?uri=change_request.do?sys_id=" +
                                     change['sys_id'] + "'>" +
                                     change['number'] +
                                     "</a>" +
                                     ": " + change['short_description']
                            )

                            annotationsReqs[dashboardID].append(_annotationReq)

                else:
                    self.loggger.debug("#makeAnnotationsForServices> No panels for service " + service)
            else:
                self.loggger.debug("#makeAnnotationsForServices> Service " + service + ' Not Found.')

        # ================================================================
        return annotationsReqs


if __name__ == '__main__':

    print("** CLEANUP START **")
    wantedOrgs = ['Staging']

    mainUtil = AnnotationsUtil(orgId=1, panelids=False)
    utils = [mainUtil]  # Main Org.
    orgs = mainUtil.getOrgs()
    for org in orgs:
        orgId = org['id']
        orgName = org['name']
        if orgName in wantedOrgs:
            utils.append(AnnotationsUtil(orgId=orgId, panelids=False))
        pass
    pass

    for autl in utils:
        DASHES = autl.dashboardList
        _numberOfDashboards = len(DASHES)
        autl.loggger.info("** Dashboards found for org %d: %d" % (autl.orgId, _numberOfDashboards))
        for DASH in DASHES:
            # if DASH['id'] != 33: # for debug
            #     continue
            #
            autl.loggger.info(
                "Processing dashboard (remains %d of %d): %s" % (_numberOfDashboards, len(DASHES), json.dumps(DASH)))
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
                    autl.loggger.info("** No annotations for dashboard %d %s %s Panel %d" % (
                    _dashboardId, DASH['uid'], DASH['title'], _panelId))
                autl.reset()
            pass
        pass
    pass

    print("**END**")
