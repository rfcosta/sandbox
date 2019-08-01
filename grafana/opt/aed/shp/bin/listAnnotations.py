#!/bin/env python

import copy
import json
import sys
from optparse import OptionParser
from logging import getLogger, DEBUG, INFO, WARNING, ERROR

sys.path.append('/opt/aed/shp/lib')
sys.path.append('/opt/aed/shp/lib/grafana')

import shputil
from helper import Helper
from alert_annotation_util import AlertAnnotationUtil


if __name__ == "__main__":

    _minutes = 15
    (_time, _timeEnd) = AlertAnnotationUtil.TimeIntervalNow(_minutes)


    parser = OptionParser(add_help_option=False)
    parser.add_option("-h", "--help",      action="help")
    parser.add_option("-o", "--options",   dest="options_file", help="Options json file", default='')
    parser.add_option("-i", "--instance",  dest="instance"   , help="SNOW Instance"    ,  default="sabredev2")
    parser.add_option("-f", "--file",      dest="jsonFile"    , help="Output json file",  default='listAnnotations.json')
    parser.add_option("-d", "--dashboard", dest="dashboardId", help="Dashboard Id"     ,  default="220")
    parser.add_option("-a", "--panel",     dest="panelId",     help="Panel Id"         ,  default="2")
    parser.add_option("-r", "--org",       dest="orgId"      , help="Org Id"           ,  default="2")
    parser.add_option("-t", "--time",      dest="time"       , help="From Time"        ,  default="1564598378")
    parser.add_option("-e", "--timeEnd",   dest="timeEnd"    , help="To Time"          ,  default="1564598378")
    parser.add_option("-g", "--grafana",   dest="grafana"    , help="Grafana Instance" ,  default="localhost")
    parser.add_option("-p", "--port",      dest="port"       , help="Grafana Port"     ,  default="3000")
    parser.add_option("-l", "--limit",     dest="limit"      , help="Limit of records" ,  default="100" )
    parser.add_option("-u", "--user",      dest="user"       , help="Grafana User"      , default='Admin')
    parser.add_option("-w", "--password",  dest="pswd"       , help="Grafana Password"  , default='IamApass01')


    (options, args) = parser.parse_args()

    # ----------------------------------------------------------------------------------------------------------
    # The following statement is just to ilustrate how to address the attributes of an object like a dictionary
    #       options.__dict__['source'] = 'VIZ' if not options.source else options.source
    # ----------------------------------------------------------------------------------------------------------

    options_from_json = dict()
    if options.options_file:
        options_from_json = AlertAnnotationUtil.LoadJson(options.options_file)

    # The following onlyt works on Python 2:
    # options_from_json.update(  (ky, val) for (ky,val) in options.__dict__.iteritems() if val  )

    options_from_json.update(  (ky, val) for (ky,val) in options.__dict__.items() if val  )


    #update back options after the overides
    options.__dict__.update(options_from_json)

    print("Options: " + str(options))

    if  not options.user or \
        not options.pswd or \
        not options.instance or \
        not options.port or \
        not options.orgId or \
        not options.limit or \
        not options.dashboardId or \
        not options.port:
        print("**ERROR** All options user/pswd/instance/port/orgId/limit/dashboard/ port must be specified from command options + options_file (-o or --options_file)")
        exit(8)

    options.regionId = 0
    URLTEMPLATE = "http://{0}:{1}@{2}:{3}/api/annotations/?orgId={4}&limit={5}&dashboardId={6}&regionId={7}"
    # &type={8}"
    grafana_url = URLTEMPLATE.format(
        options.user,
        options.pswd,
        options.grafana,
        options.port,
        options.orgId,
        options.limit,
        options.dashboardId,
        options.regionId
    )

    print (grafana_url)

    autl = AlertAnnotationUtil(orgId=options.orgId, instanceName=options.instance)

    _dashAnnotations = autl.getAnnotationsOnDashboardPanel(dashboardId=options.dashboardId, \
                                                           panelId=options.panelId, \
                                                           fromTime=options.time, toTime=options.timeEnd \
                                                          )
    _numberOfAnnotationsReturned = len(_dashAnnotations)

    autl.loggger.info("** Ann returned %d" % (_numberOfAnnotationsReturned))

    _incident   = 'INC2543646'
    _instance   = 'sabredev2'
    _inc_sys_id = 'b3783ae8dbcffb0821421ffa6896194d'
    _inc_descr  = '[Alert3450155] Service Health Portal: WARNING: Payment Internet Payment Engine Transaction Count is 35 which is below the dynamic threshold'

    _annotation = copy.deepcopy(_dashAnnotations[0])
    _annotation['text'] = autl.makeSnowHTMLReference(sys_id=_inc_sys_id, number=_incident, short_description=_inc_descr)



    response = autl.updateAnnotation( _annotation )

