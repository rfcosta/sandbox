#!/bin/env python

import sys
import json
import time

sys.path.append('/opt/aed/shp/lib')
from shpannotations import ShpAnnotations

MAINVERBOSE = True
PRINTANNOTATIONS = False
DEBUG = 'NO'

def shout(msg):
    if MAINVERBOSE:
        print (time.strftime('%Y-%m-%d %H:%M:%S') + " " + msg)

def myCalcHash(_annotation):
    import re
    _sysId = ''
    _XSYSID = re.compile('https[:][/][/]\S+\?sys_id=([0123456789abcdef]{32})')
    _text = _annotation.get('text')
    if _text:
        _tokens = _XSYSID.findall(_text)
        if _tokens.__len__() > 0:
            _sysId = _tokens[0]
    return _sysId

def listOrg(cls):
    print("#listOrg> " + json.dumps(cls.current_org))


def process_annotations(cls):

    _curr = cls.setCurrentOrg(ORG=cls.current_org['id'])
    _orgId      = _curr['id']
    _orgName    = _curr['name']
    listOrg(cls)
    _newAnnotations = cls.makeAnnotationsForServices()
    shout("process_annotations> Returned from makeAnnotationsForServices: " + str(_orgId) + " " + _orgName + " --> " + json.dumps(_newAnnotations) )


    # These commented lines is how you use your own hash calculator function
    #        thismodule = sys.modules[__name__]
    #        hashcalc   = getattr(thismodule,'myCalcHash')
    #        _existingAnnotations = cls.getAnnotations(HASH=hashcalc)
    # To use the default hash:
    ## _existingAnnotations = cls.getAnnotations()  # Hashes thru method on cls (cls.parseSysId)


    for _dashboardId in _newAnnotations.keys():

        # These commented lines is how you use your own hash calculator function
        # thismodule = sys.modules[__name__]
        # hashcalc   = getattr(thismodule,'myCalcHash')
        # _existingAnnotations = cls.getAnnotations(HASH=hashcalc, DASHBOARDID=_dashboardId)
        _existingAnnotations = cls.getAnnotations(DASHBOARDID=_dashboardId)  # Hashes thru method on cls (cls.parseSysId)

        if PRINTANNOTATIONS:
            cls.printAnnotations(_existingAnnotations)

        for _newAnnotation in _newAnnotations[_dashboardId]:
            d = _newAnnotation['dashboardId']
            p = _newAnnotation['panelId']

            # hash = myCalcHash(_newAnnotation)
            hash = cls.parseSysId(_newAnnotation)

            if _dashboardId == d:
                # Find annotations to be cleaned up
                _dash_panel_hash = (d, p, hash)
                if _existingAnnotations.get(_dash_panel_hash):
                    _rangesOnPanel = cls.getRangeList( _existingAnnotations, d, p, hash)
                    shout("#process_annotations: new range/annotation: " + json.dumps(_newAnnotation))
                    shout("#process_annotations: Ranges to be deleted: " + str(_rangesOnPanel))

                    for _range in _rangesOnPanel:
                        shout("process_annotations>    Range regionId " + str(_range))
                        _delresp = cls.deleteAnnotationRange(_range)
                        shout("process_annotations>    Range deletion response: " + json.dumps(_delresp))

                # FORCE DATES FOR DEBUG PURPOSES - COMMENT THIS FOR REAL CODE
                # ===== ===== === ===== ======== = ======= ==== === ==== ====
                #_newAnnotation['time']    = 1541799000000     # 15:30      # 1541797200000  # 11/9 15:00
                #_newAnnotation['timeEnd'] = 1541802600000     # 16:30      # 1541800800000  # 11/9 16:00

                # Add new annotation after clean up of existing ones with same hash
                shout("#process_annotations>  Range to be added: " + json.dumps(_newAnnotation))
                _createresp = cls.createAnnotation(_newAnnotation)
                shout("process_annotations>   Range creation response: " + json.dumps(_createresp))

            else:
                shout("process annotations> *ERROR* something is broken, dashboard id not in sync with internal code: " +
                      " Id from annotation " + str(d) +
                      " does not match the one from the internal list " + str(_dashboardId)
                     )

if __name__ == '__main__':
    main = ShpAnnotations(ORGID=1,DEBUG=str(DEBUG))  # make one object for region 1

    orgs_dict = main.getOrgs()
    org_list = [org['id'] for org in orgs_dict['orgs'][1:]]

    shout("# Secondary Organizations are: " + str(org_list))


    helpers = [ main ]
    for _org in org_list:
        _orgName = orgs_dict.get(int(str(_org)))
        helpers.append(ShpAnnotations(ORGID=_org,DEBUG=str(DEBUG)))
        shout("#shpchangeranges> helper loaded for organisation " + str(_org) + " " + _orgName)

    for helper in helpers:
        listOrg(helper)
        process_annotations(helper)

