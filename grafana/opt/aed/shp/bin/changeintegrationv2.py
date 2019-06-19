#!/bin/env python

import sys
import json
import time

sys.path.append('/opt/aed/shp/lib')
sys.path.append('/opt/aed/shp/lib/grafana')

from annotations_util import AnnotationsUtil


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
                cls.loggger.info("** Ann returned %d" % (_existingReturned))
                cls.setLimitStatus(state=(_existingReturned >= cls.limit))
                if _existingReturned > 0:
                    _result = cls.loadLatestAnnotationsReturnedFromGrafana(_existingAnnotations)
                if cls.limitReached:
                    cls.loggger.warn("** Too many annnotations on panel; Inserts turned off")
            pass

            if key in cls.existingAnnotations:
                _existingChange = cls.existingAnnotations[key]
                _existingRegion = max(_existingChange.keys())

                _annotationStart = _existingChange[_existingRegion][0]
                _annotationEnd   = _existingChange[_existingRegion][1]
                _match = (_newAnnotation['text']   == _annotationStart['text']) and (_newAnnotation['text']   == _annotationEnd['text'])   and \
                         (_annotationStart['time'] == _newAnnotation['time'])   and (_annotationEnd['time']   == _newAnnotation['timeEnd'])
                if _match:
                    cls.loggger.info("** Annotation Region %d matched therefore will not be updated" % (_existingRegion))
                else:
                    _updateResp = cls.updateAnnotationPair(_newAnnotation, _existingChange[_existingRegion])
                    cls.loggger.info("Annotation Region %d %s Update response: %s" % (_existingRegion, json.dumps(_newAnnotation),json.dumps(_updateResp)))
            else:
                if cls.limitReached:
                    cls.logger.warn("** Too many annnotations on panel; Inserts turned off: %s" % (json.dumps(_newAnnotation)))
                else:
                    _createResp = cls.createAnnotationPair(_newAnnotation)
                    cls.loggger.info("Annotation %s Creation response: %s" % (json.dumps(_newAnnotation), json.dumps(_updateResp)))
                pass
            pass


if __name__ == '__main__':

    print("** CHANGE INTEGRATION START **")
    wantedOrgs = ['Staging'] # Other than main

    mainUtil = AnnotationsUtil(orgId=1,panelids=True)  # For testing only get orgId=2 because there are fewer dashboards
    utils = [mainUtil]  # Main Org.
    orgs = mainUtil.getOrgs()
    for org in orgs:
        orgId   = org['id']
        orgName = org['name']
        if orgName in wantedOrgs:
            utils.append(AnnotationsUtil(orgId=orgId, panelids=False))
        pass
    pass

    for _util in utils:
        process_annotations(_util)
    pass

    print("** CHANGE INTEGRATION END **")


