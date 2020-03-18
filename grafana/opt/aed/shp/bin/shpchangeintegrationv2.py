#!/bin/env python3

import sys
import json

sys.path.append('/opt/aed/shp/lib')
sys.path.append('/opt/aed/shp/lib/grafana')

import shputil

from annotations_util import AnnotationsUtil

shputil.check_logged_in_user('centos')

def process_annotations(cls):

    _newAnnotations = cls.makeAnnotationsRequestsForServices()
    loggger = cls.loggger
    loggger.debug("** NEW ANN: %d" % (len(_newAnnotations)))

    cls.loggger.info("** Will process %d dashboards" % (len(_newAnnotations.keys())))

    for _dashboardId in _newAnnotations.keys():

        _lastPanelId = 0
        for _newAnnotation in _newAnnotations[_dashboardId]:

            _panelId = _newAnnotation['panelId']
            _change  = cls.parseSysId(_newAnnotation['text'])
            key = (_dashboardId, _panelId, _change)

            if _panelId != _lastPanelId:
                _lastPanelId = _panelId
                cls.loggger.info("** Loading Existing Annotations from Dashboard %d Panel %d" % (_dashboardId, _panelId))
                cls.reset()
                _existingAnnotations = cls.getAnnotationsOnDashboardPanel(dashboardId=_dashboardId, panelId=_panelId)
                _existingReturned = len(_existingAnnotations)
                cls.loggger.info("** Ann returned %d" % _existingReturned)
                cls.setLimitStatus(state=(_existingReturned >= cls.limit))
                if _existingReturned > 0:
                    _result = cls.loadLatestAnnotationsReturnedFromGrafana(_existingAnnotations)
                if cls.limitReached:
                    cls.loggger.warn("** Too many annnotations on panel; Inserts turned off")
            pass

            if key in cls.existingAnnotations:
                _existingChange = cls.existingAnnotations[key]
                _existingRegion = max(_existingChange.keys())  # For new Grafana the regioId is initialized with -1
                _match = True

                if len(_existingChange[_existingRegion]) == 1:   # New Grafana
                    _uniqueAnnotation = _existingChange[_existingRegion][0]
                    _match = (_uniqueAnnotation['text']      == _newAnnotation['text']) and \
                             (_uniqueAnnotation['time']      == _newAnnotation['time']) and \
                             (_uniqueAnnotation['timeEnd']   == _newAnnotation['timeEnd'])
                    pass
                else:
                    if len(_existingChange[_existingRegion]) > 0:
                        _annotationStart = _existingChange[_existingRegion][0]
                    else:
                        _annotationStart = dict(text='Missing annotation', time=0, dashboardId=_dashboardId, panelId=_panelId)
                    pass

                    if len(_existingChange[_existingRegion]) > 1:
                        _annotationEnd = _existingChange[_existingRegion][1]
                    else:
                        _annotationEnd = dict(text=_annotationStart['text'], time=0, dashboardId=_dashboardId, panelId=_panelId)
                    pass

                    _match = (_newAnnotation['text']   == _annotationStart['text']) and (_newAnnotation['text'] == _annotationEnd['text']) and \
                             (_annotationStart['time'] == _newAnnotation['time'])   and (_annotationEnd['time'] == _newAnnotation['timeEnd'])
                pass

                if _match:
                    cls.loggger.info("** Annotation Region %d matched therefore will not be updated" % _existingRegion)
                else:
                    _updateResp = cls.updateAnnotationPair(_newAnnotation, _existingChange[_existingRegion])
                    cls.loggger.info("Annotation Region %d %s Update response: %s" % (_existingRegion, json.dumps(_newAnnotation), _updateResp))
            else:
                if cls.limitReached:
                    cls.loggger.warn("** Too many annnotations on panel; Inserts turned off: %s" % (json.dumps(_newAnnotation)))
                else:
                    _createResp = cls.createAnnotationPair(_newAnnotation)
                    cls.loggger.info("Annotation %s Creation response: %s" % (json.dumps(_newAnnotation), _createResp))
                pass
            pass


if __name__ == '__main__':

    print("** CHANGE INTEGRATION START **")
    wantedOrgs = ['Staging']   # Other than main

    mainUtil = AnnotationsUtil(orgId=1, panelids=True)  # start with Main Org.
    utils = [mainUtil]  # Main Org.
    orgs = mainUtil.getOrgs()
    for org in orgs:
        orgId   = org['id']
        orgName = org['name']
        if orgName in wantedOrgs:
            utils.append(AnnotationsUtil(orgId=orgId, panelids=True))
        pass
    pass

    for _util in utils:
        process_annotations(_util)
    pass

    print("** CHANGE INTEGRATION END **")
