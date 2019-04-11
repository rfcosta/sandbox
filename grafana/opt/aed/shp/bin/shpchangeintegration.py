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
                # Find if new annotation is already there for the same change, delete any duplicates if any
                _FOUND_SAME_RANGE = False
                _dash_panel_hash = (d, p, hash)
                _rangesOnPanel = _existingAnnotations.get(_dash_panel_hash)

                if _rangesOnPanel:
                    shout("#process_annotations: new notation range: " + json.dumps(_newAnnotation))

                    _FOUND_SAME_RANGE = False
                    for _existingRange in _rangesOnPanel:
                        shout("#process_annotations: Existing Range: " + str(_existingRange['regionId']))

                        _annotationPair =  _existingRange['annotations']
                        #If a range doesnt contain exactly an annotation pair, leave it alone
                        if _annotationPair.__len__() == 2:
                            if _annotationPair[0]['time'] < _annotationPair[1]['time']:
                                _annotationStart = _annotationPair[0]
                                _annotationEnd   = _annotationPair[1]
                            else:
                                _annotationStart = _annotationPair[1]
                                _annotationEnd   = _annotationPair[0]

                            try:
                                if (not _FOUND_SAME_RANGE) and (_newAnnotation['text'] == _annotationStart['text']) and (_newAnnotation['text'] == _annotationEnd['text']) and (_annotationStart['time'] == _newAnnotation['time']) and (_annotationEnd['time'] == _newAnnotation['timeEnd']):
                                    _FOUND_SAME_RANGE = True
                                else:
                                    _regionId = _existingRange['regionId']
                                    shout("process_annotations>    Range regionId " + str(_regionId))
                                    _delresp = cls.deleteAnnotationRange(_regionId)
                                    shout("process_annotations>    Range deletion response: " + json.dumps(_delresp))
                            except Exception as E:
                                shout("#process_annotations> deleteAnnotatioRange exception: " + str(E.message))


                # Add new annotation after clean up of existing ones with same hash
                if _FOUND_SAME_RANGE:
                    shout("#process_annotations>  Range already there: " + json.dumps(_newAnnotation))
                else:
                    try:
                        shout("#process_annotations>  Range to be added: " + json.dumps(_newAnnotation))
                        _createresp = cls.createAnnotation(_newAnnotation)
                        shout("process_annotations>   Range creation response: " + json.dumps(_createresp))
                    except Exception as E:
                        shout("#process_annotations> createAnnotation exception: " + str(E.message))

            else:
                shout("process annotations> *ERROR* something is broken, dashboard id not in sync with internal code: " +
                      " Id from annotation " + str(d) +
                      " does not match the one from the internal list " + str(_dashboardId)
                     )

if __name__ == '__main__':
    main = ShpAnnotations(ORGID=1,DEBUG=str(DEBUG))  # make one object for region 1

    orgs_dict = main.getOrgs()
    #org_list = [org['id'] for org in orgs_dict['orgs'][1:]]
    org_list = [org['id'] for org in orgs_dict['orgs'] if org['name'] != 'Main Org.' ]

    shout("# Secondary Organizations are: " + str(org_list))


    helpers = [ main ]
    for _org in org_list:
        _orgName = orgs_dict.get(int(str(_org)))
        helpers.append(ShpAnnotations(ORGID=_org,DEBUG=str(DEBUG)))
        shout("#shpchangeranges> helper loaded for organisation " + str(_org) + " " + _orgName)

    for helper in helpers:
        listOrg(helper)
        try:
            process_annotations(helper)
        except Exception as E:
            shout("# ERROR process_annotations helper: " + str(E.message))

    shout("#End run ---------------------")

