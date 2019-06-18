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

    DASHES = cls.dashboardList
    _numberOfDashboards = len(DASHES)
    cls.loggger.info("** Dashboards found for org %d: %d" % (autl.orgId, _numberOfDashboards))
    for DASH in DASHES:
        # if DASH['id'] != 33: # for debug
        #     continue
        #
        cls.loggger.info(
            "Processing dashboard (remains %d of %d): %s" % (_numberOfDashboards, len(DASHES), json.dumps(DASH)))
        _numberOfDashboards -= 1
        _dashboardId = DASH['id']
        _incomingDashAnnotations = _newAnnotations[_dashboardId]
        _panelIdList = DASH['panelids']
        for _panelId in _panelIdList:
            # if _panelId != 1:  # for debug
            #     continue
            cls.loggger.info("** Processing Panel %d" % (_panelId))
            _dashAnnotations = cls.getAnnotationsOnDashboardPanel(dashboardId=_dashboardId, panelId=_panelId)
            _numberOfAnnotationsReturned = len(_dashAnnotations)

            cls.loggger.info("** Ann returned %d" % (_numberOfAnnotationsReturned))

            cls.setLimitStatus(state=(_numberOfAnnotationsReturned == autl.limit))
            if _numberOfAnnotationsReturned > 0:
                _result = cls.loadAnnotationsReturnedFromGrafana(_dashAnnotations)
                #autl.checkDuplicates()
            # else:
            #     cls.loggger.info("** No annotations for dashboard %d %s %s Panel %d" % (
            #     _dashboardId, DASH['uid'], DASH['title'], _panelId))
            cls.reset()
        pass
    pass

    pass

if __name__ == '__main__':

    print("** CHANGE INTEGRATION START **")
    wantedOrgs = ['Staging'] # Other than main
    wantedOrgs = []

    mainUtil = AnnotationsUtil(orgId=2,panelids=True)
    utils = [mainUtil]  # Main Org.
    orgs = mainUtil.getOrgs()
    for org in orgs:
        orgId   = org['id']
        orgName = org['name']
        if orgName in wantedOrgs:
            utils.append(AnnotationsUtil(orgId=orgId, panelids=False))
        pass
    pass


    process_annotations(utils[0])
