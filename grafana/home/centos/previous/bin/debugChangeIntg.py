#!/bin/env python

import sys
import json
import time

sys.path.append('/opt/aed/shp/lib')
from shpannotations import ShpAnnotations

def shout(msg):
    print (time.strftime('%Y-%m-%d %H:%M:%S') + " " + msg)

def listOrg(cls):
    print("#listOrg> " + json.dumps(cls.current_org))

def printAnnotations(_existingAnnotations):

    for _home in _existingAnnotations.keys():
        shout("#printAnnotations> Group=" + str(_home))
        d, p, h = _home
        for _region in _existingAnnotations[(d, p, h)].keys():
            _range = _existingAnnotations[(d, p, h)][_region]
            _c = 0
            for _ann in _range:
                shout("#printAnnotations> _existingAnnotations: DASH=%d PANEL=%d HASH='%s' REGION=%s [%2d]: \t %s" %
                      (d, p, h, _region, _c, json.dumps(_ann))
                      )
                _c = _c + 1


def process_annotations(cls):

    _curr = cls.setCurrentOrg(ORG=cls.current_org['id'])
    _orgId      = _curr['id']
    _orgName    = _curr['name']
    listOrg(cls)
    _newAnnotations = cls.makeAnnotationsForServices()
    #    shout("process_annotations> Returned from makeAnnotationsForServices: " + str(_orgId) + " " + _orgName + " --> " + json.dumps(_newAnnotations) )


    for _dashboardId in _newAnnotations.keys():

        _existingAnnotations = cls.getAnnotations(DASHBOARDID=_dashboardId)  # Hashes thru method on cls (cls.parseSysId)
        printAnnotations(_existingAnnotations)

        for _newAnnotation in _newAnnotations[_dashboardId]:

            shout("#_newAnnotation in _newAnnotations[_dashboardId]: " + json.dumps(_newAnnotation))

            d = _newAnnotation['dashboardId']
            p = _newAnnotation['panelId']

            # hash = myCalcHash(_newAnnotation)
            hash = cls.parseSysId(_newAnnotation)

            if _dashboardId == d:
                # Find annotations to be cleaned up
                _dash_panel_hash = (d, p, hash)
                if _existingAnnotations.get(_dash_panel_hash):
                    _rangesOnPanel = _existingAnnotations[_dash_panel_hash]

                    shout("#process_annotations: Ranges to be deleted:")

                    for _range in _rangesOnPanel.keys():
                        shout("range in _rangesOnPanel.keys>    Range regionId " + _range + ": " + json.dumps(_rangesOnPanel[_range]))
                        _delresp = cls.deleteAnnotationRange(_range)
                        shout("process_annotations>    Range deletion response: " + json.dumps(_delresp))

                ####shout("#process_annotations>  Range to be added: " + json.dumps(_newAnnotation))
                #### _createresp = cls.createAnnotation(_newAnnotation)
                #### shout("process_annotations>   Range creation response: " + json.dumps(_createresp))

            else:
                shout("process annotations> *ERROR* something is broken, dashboard id not in sync with internal code: " +
                      " Id from annotation " + str(d) +
                      " does not match the one from the internal list " + str(_dashboardId)
                     )

if __name__ == '__main__':
    main = ShpAnnotations(ORGID=2,DEBUG='YES')  # make one object for region 1
    orgs_dict = main.getOrgs()

    listOrg(main)
    process_annotations(main)



