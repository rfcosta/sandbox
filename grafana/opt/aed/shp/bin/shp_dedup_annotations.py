#!/usr/bin/python

import json
import os
import sys
import datetime
import re

sys.path.append('/opt/aed/shp/lib')
sys.path.append( '/opt/aed/shp/lib/grafana')

from helper import Helper

class Annotations():

    def __init__(self, *args, **kwargs):
        self.orgId    = kwargs.get('orgId', 1)
        self.helper   = Helper(self.orgId)
        self.DEBUG    = kwargs.get('debug', False)
        if self.DEBUG == 'True':
            self.DEBUG = True

    def getDashboards(self, *args, **kwargs):
        resp = self.helper.api_get_with_params("search", {'type': 'dash-db'})
        dashboards = json.loads(resp.content)
        return dashboards

    def getAnnotationsOnDashboard(self, *args, **kwargs):
        params = dict(type='annotation', dashboardId=kwargs.get('dashboardId',0), limit=kwargs.get('limit',5000))
        _panelId = kwargs.get('panelId',None)
        if _panelId:
            params['panelId'] = _panelId

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

    def deleteAnnotation(self,annotationId):
        params = dict(orgId=self.orgId)
        resp = self.helper.api_delete("annotations/" + str(annotationId))
        if resp.status_code != 200:
            raise Exception("Error deleting annotation " + str(annotationId))
        self.deletionFromGrafana = json.loads(resp.content)
        return self.deletionFromGrafana


    def parseSysId(self,_annotation):
        _sysId = ''
        _XSYSID = re.compile('https[:][/][/]\S+\?sys_id=([0123456789abcdef]{32})')
        _text = _annotation.get('text')
        if _text:
            _tokens = _XSYSID.findall(_text)
            if _tokens.__len__() > 0:
                _sysId = _tokens[0]
        return _sysId

    def parseChange(self,_annotation):
        _change = ''
        _XCHANG = re.compile('https[:][/][/]\S+\?sys_id=[0123456789abcdef]{32}..CHG(\d+)')
        _text = _annotation.get('text')
        if _text:
            _tokens = _XCHANG.findall(_text)
            if _tokens.__len__() > 0:
                _change = _tokens[0]
        return 'CHG' + _change

    def epoch2date(epoch):
        return datetime.datetime.fromtimestamp(float(epoch // 1000))

    def epochMinute(epoch):
        return int(epoch) // 60 * 60

    def conceal(pwd):
        return pwd[0].ljust(pwd.__len__(), '*') + pwd[-1]

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

    #   ===========================================================================================
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

    #   ===========================================================================================
    def loadAnnotation(self, _annt, annotations, **kwargs):

        if self.DEBUG:
            print("#loadAnnotations> Annotation From Grafana: " + json.dumps(_annt, indent=4))

        _HASH = kwargs.get('HASH')
        if not _HASH:
            _HASH = getattr(self,"parseSysId")

        _hash = _HASH(_annt)

        if _hash:

            if (_annt.get("region_id")):  # Coming from database query instead of API
                _annt['regionId'] = _annt.get("region_id")
                _annt['dashboardId'] = _annt.get("dashboard_id")
                _annt['panelId'] = _annt.get("panel_id")
                _annt['time'] = _annt.get("epoch")

            _annotation = {"id": int(str(_annt.get("id"))),
                           "regionId": int(str(_annt.get("regionId"))),
                           "dashboardId": int(str(_annt.get("dashboardId"))),
                           "panelId": _annt.get("panelId"),
                           "hash": _hash,
                           "time": _annt.get("time"),
                           "text": _annt.get("text")
                           }

            # Range is the unique home of the range annotation. i.e. Dashboard + Panel + Hash
            # A homerange is a list of ranges with a regionId that has two annotation with the same regionId

            _homerange = (_annotation['dashboardId'], _annotation["panelId"], _annotation['hash'])
            _regionId = _annotation["regionId"]

            # if not annotations.get(_homerange):
            #     annotations[_homerange] = []  # Make the group be a list of ranges object
            annotations.setdefault(_homerange, {})

            annotations[_homerange].setdefault(_regionId,{"regionId": _regionId, "annotations": []})

            # _region['annotations'].insert(0, _annotation)
            annotations[_homerange][_regionId]['annotations'].append(_annotation)

            return annotations

     #   ===========================================================================================
    def printAnnotations(self, annotations):
        for _homerange in annotations.keys():
            # print("#getAnnotations> _homerange=" + str(_homerange))
            d, p, h = _homerange
            _regionlist = [_region['regionId'] for _region in annotations[_homerange].keys()]

            print(" ")
            print("Region list for " + str(_homerange) + " = " + str(_regionlist))

            for _region in annotations[(d, p, h)].keys():
                _regionId  = annotations[(d, p, h)][_region]['regionId']
                _rangeList = annotations[(d, p, h)][_region]['annotations']
                _c = 0
                startend = {"0": "start", "1": "end"}
                for _ann in _rangeList:
                    _change = self.parseChange(_ann)
                    _id = _ann.get('id', 0)
                    _time = self.epoch2date(_ann.get('time'))
                    _x = startend.get(str(min(1, int(_id) - int(_regionId))), " ")

                    #
                    # print("#    DASH=%d PANEL=%d HASH='%s' REGION=%s [%2d]: \t %s" %
                    #       (d, p, h, _region, _c, json.dumps(_ann, indent=4))
                    #       )

                    print(" |   DASH=%d PANEL=%d HASH='%s' REGION=%8s [%-5s]: \t %12d %-10s %s %13s" %
                          (d, p, h, _regionId, _x, _id, _change, _time, _ann.get('time'))
                          )
                    _c = _c + 1

    #   ===========================================================================================
    def dumpAnnotations(self, annotations, file=''):
        import copy

        if file:
            buffer = copy.deepcopy(annotations)

            for _homerange in annotations.keys():
                _regions = dict(regionList=copy.deepcopy(annotations[_homerange]),
                                regionsKey=str(_homerange)
                                )
                result = self.WriteFile(file, _regions, option="a")
                if result:
                    return result
        else:
            for _homerange in annotations.keys():
                # print("#getAnnotations> _homerange=" + str(_homerange))
                d, p, h = _homerange
                _regionlist =  annotations[_homerange].keys()

                print(" ")
                print("Region list for " + str(_homerange) + " = " + str(_regionlist))

                print(json.dumps(annotations[_homerange], indent=4))

        return ''

    #   ===========================================================================================
    # def getAnnotations(self, *args, **kwargs):
    #
    #     self = ShpAnnotations(ORGID=1)
    #
    #     _orgId = kwargs.get('ORGID')
    #     if not _orgId:
    #         _orgId = 1
    #
    #     _HASH = kwargs.get('HASH')
    #     if not _HASH:
    #         _HASH = getattr("parseSysId")
    #
    #     _annotations = []
    #     _dashboardId = kwargs.get('DASHBOARDID')
    #     _limit = kwargs.get('LIMIT', 500)
    #
    #     if _dashboardId:
    #         _annotations = self.grafanaAPI('get', 'annotations', ORGID=_orgId, LIMIT=_limit, TYPE='annotation',
    #                                        DASHBOARDID=_dashboardId)
    #     else:
    #         _annotations = self.grafanaAPI('get', 'annotations', ORGID=_orgId, LIMIT=_limit, TYPE='annotation')
    #
    #     annotations = {}
    #     print("#getAnnotations: annotations object = " + json.dumps(_annotations))
    #     for _annt in _annotations:
    #         print("#getAnnotations> Annotation From Grafana: " + json.dumps(_annt, indent=4))
    #         annotations = loadAnnotation(_annt, annotations, HASH=_HASH)
    #
    #     # if self.VERBOSE or self.DEBUG:
    #     #     printAnnotations(annotations)
    #
    #     return annotations
    #
    #   ===========================================================================================
    def getAnnotationsFromFile(self, *args, **kwargs):
        VERBOSE = False
        fileName = kwargs.get('file', 'annotations1,json')
        _HASH = kwargs.get('HASH')

        _annotations = self.LoadFile(fileName)

        annotations = {}
        if VERBOSE:
            print("#getAnnotationsFromFile: annotations object = " + json.dumps(_annotations))

        for _annt in _annotations:
            if VERBOSE:
                print("#getAnnotationsFromFile> Annotation From Grafana: " + json.dumps(_annt, indent=4))

            annotations = self.loadAnnotation(_annt, annotations, HASH=_HASH)
            if not annotations:
                print("Empty results from loadAnnotation for " + json.dumps(_annt, indent=4))
                print("******************")
                print("Annotations DB so far: " + json.dumps(annotations, indent=4))

        # printAnnotations(annotations)

        return annotations


if __name__ == "__main__":

    args   = None
    kwargs = dict(orgId = 1)
    try:
        if len(sys.argv) > 1:
            kwargs['orgId'] = int(sys.argv[1])
    except Exception as E:
        raise Exception('Invalid parameter on command line: ' + E.message)

    ANN = Annotations(orgId=kwargs['orgId'], )
    _HASH = getattr(ANN,'parseSysId')


    _dashboards = ANN.getDashboards()

    for _dash in _dashboards:

        _annotationsDB = {}
        _dashboardId = _dash.get('id')

        _annotations = ANN.getAnnotationsOnDashboard(dashboardId=_dashboardId)
        for _annt in _annotations:
            _annotationsDB = ANN.loadAnnotation(_annt, _annotationsDB, HASH=_HASH)

        if ANN.DEBUG:
            ANN.printAnnotations(_annotationsDB)

        for _changeKey in _annotationsDB.keys():
            (_d, _p, _h) = _changeKey
            _regionList = _annotationsDB[_changeKey].keys()

            if _regionList.__len__() > 1:  # Duplicates if more than 1
                _latestToKeep = max(_regionList)
                _toDelete = []

                for _region in _annotationsDB[_changeKey]:
                    _regionId = _region['regionId']
                    if _regionId != _latestToKeep:
                        _annotationsOnRegion = _region['annotations']
                        if len(_annotationsOnRegion) > 1:
                            _annotationId1 = _annotationsOnRegion[0]['id']
                            _annotationId2 = _annotationsOnRegion[1]['id']
                            _toDelete.append((_regionId, _annotationId1, _annotationId2))

                if _toDelete.__len__() < 20:
                    print("Dashboard=%s, Panel=%s, Hash=%s, Deletelist: %s" % (_d, _p, _h, str(_toDelete)))
                else:
                    print("Dashboard=%s, Panel=%s, Hash=%s, Duplicates: %s" % (_d, _p, _h, _toDelete.__len__()))

                print("Dash %d, Panel %d, Hash %s, Kept %d " % (_d, _p, _h, _latestToKeep))

                for regionToDelete in _toDelete:
                    _regionId, _annotationId1, _annotationId2 = regionToDelete
                    #result = ANN.deleteAnnotationByRegion(regionId)
                    result1 = ANN.deleteAnnotation(_annotationId1)
                    result2 = ANN.deleteAnnotation(_annotationId2)
                    print("Ann Region %d: A1: %d %s, A2: %d %s" % (_region, _annotationId1, result1, _annotationId2, result2))

            else:
                print("Dashboard=%s, Panel=%s, Hash=%s No duplicates found" % (_d, _p, _h) )

print ("*** END DEDUP ***")
