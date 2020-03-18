import sys
import os
import json
import datetime
import argparse
import base64
import requests
import re
import copy
import time
#import pytz

sys.path.append('/opt/aed/shp/lib')
import shputil

class ShpAnnotations():
    """The shp_annotations object wraps features of :class:`requests.Session`
       and grafana API to mantain annotation on Grafana
    """

    # ===================================================================================================================
    # S T A T I C   M E T H O D S
    # ===================================================================================================================

    @staticmethod
    def encodeService(service):
        service_name = service.replace(" -", "-").replace("- ", "-").replace("_", "-").replace(" ","-")
        return service_name

    #pytz dependency so don't define gertEpoch since is not used for now
    #@staticmethod
    #def getEpoch(timestamp, format='%Y-%m-%d %H:%M', zone='US/Central'):
    #     offset = datetime.datetime.now(pytz.timezone(zone)).strftime('%z')
    #     hereIAm = time.strftime("%z",time.gmtime())
    #     offsetSeconds = (int(offset) - int(hereIAm)) / 100 * 3600
    #     dateValue = datetime.datetime.strptime(timestamp, format)
    #     epochSeconds = int(time.mktime(dateValue.timetuple()))
    #     epochSeconds = epochSeconds - offsetSeconds
    #     return int(str(epochSeconds) + '000'), offset, offsetSeconds, hereIAm


    @staticmethod
    def load_file(filename):
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

    @staticmethod
    def validate_datetime(input):
        _XNUMBER = re.compile(r'^\d+$')
        #print(" %s type is %s" % (input, type(input).__name__))
        if type(input).__name__ == 'datetime':
            return input

        if _XNUMBER.match(str(input)):
            nowEpoch = (int(time.time()) // 60) * 60
            backEpoch = nowEpoch - (int(str(input)) * 60)
            backMinute = datetime.datetime.fromtimestamp(backEpoch)
            return backMinute

        if type(input).__name__ == 'str':
            try:
                input = ' '.join(input.split('T'))
                return datetime.datetime.strptime(input, '%Y-%m-%d %H:%M')
            except ValueError:
                msg = 'Not a valid date: %s' % input
                raise argparse.ArgumentTypeError(msg)


    @staticmethod
    def parseSysId(_annotation):
        _sysId = ''
        _XSYSID = re.compile('https[:][/][/]\S+\?sys_id=([0123456789abcdef]{32})')
        _text = _annotation.get('text')
        if _text:
            _tokens = _XSYSID.findall(_text)
            if _tokens.__len__() > 0:
                _sysId = _tokens[0]
        return _sysId


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

    #===================================================================================================================
    # D E B U G
    #===================================================================================================================
    def debug(self,msg):
        if (self.DEBUG):
            print(time.strftime('%Y-%m-%d %H:%M:%S') + " " + msg)


    #===================================================================================================================
    # C O N S T R U C T O R
    #===================================================================================================================

    def __init__(self, *args, **kwargs):

        self.MAXTRIES = 3
        self.DEBUG = False
        self.VERBOSE = False
        self.CONFIG  = shputil.get_config()
        self.CONFIG_FILE_NAME = self.CONFIG.get('service_configuration_file')
        self.CHANGE_FILE_NAME = self.CONFIG.get('change_configuration_file')

        _aDEBUG     = kwargs.get('DEBUG')
        if _aDEBUG:
            if _aDEBUG == 'YES':
                self.DEBUG = True
            if _aDEBUG == "NO":
                self.DEBUG = False

        _aVERBOSE     = kwargs.get('VERBOSE')
        if _aVERBOSE:
            if _aVERBOSE == 'YES':
                self.VERBOSE = True
            if _aVERBOSE == "NO":
                self.VERBOSE = False


        self.SSO_MAIN = 'https://login.sabre.com/wam/json'
        self.URL      = 'http://' + self.CONFIG.get("grafana_host") # 'http://localhost:3000'
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json"
        })
        self._user      = self.CONFIG.get("grafana_user")
        self._password  = self.CONFIG.get("grafana_pass")

        self._snowuser      = self.CONFIG.get("servicenow_user")
        self._snowpassword  = self.CONFIG.get("servicenow_pass")
        self._snowinstance  = self.CONFIG.get("servicenow_instance") # sabredev2 ?

        self.orgs_dict   = self.getOrgs()
        self.debug("#Constructor self.orgs_dict: " + json.dumps(self.orgs_dict))

        _aUSER      = kwargs.get('user')
        _aPASSWORD  = kwargs.get('password')
        _sUSER      = kwargs.get('suser')
        _sPASSWORD  = kwargs.get('spassword')
        _aSSO       = kwargs.get('SSO')  # Future implementations, not used mow
        _aURL       = kwargs.get('URL')
        _aSNOW      = kwargs.get('SNOW')
        _aORGID     = kwargs.get('ORGID')

        if _aUSER:
            self._user = _aUSER
        if _aPASSWORD:
            self._password = _aPASSWORD
        if _sUSER:
            self._snowuser = _sUSER
        if _sPASSWORD:
            self._snowpassword = _sPASSWORD
        if _aSSO:
            self.SSO_MAIN = _aSSO
        if _aURL:
            self.URL = _aURL
        if _aSNOW:
            self._snowinstance = _aSNOW

        if _aORGID:
            _nOrgId = int(str(_aORGID))
            self.current_org = self.setCurrentOrg(_nOrgId)
        else:
            self.current_org = self.setCurrentOrg(1)

        self.debug("#Constructor self.current_org: " + json.dumps(self.current_org))



        # self._XHEADER   = re.compile('[,]+')
        # self._XDATETIME = re.compile('\d\d\d\d[-]\d\d[-]\d\d\s\d\d[:]\S+')
        # self._XCSV      = re.compile('([^,]+)[,]?|[,]')
        # self._XIGN      = re.compile(r'^$|^\s+$|Process finished with exit code')
        # self._XCOLON    = re.compile('\:')

        self.debug("DEBUG-- URL = " + self.URL)



    #===================================================================================================================
    # N E T W O R K   r e l a t e d   m e t h o d s
    #===================================================================================================================

    def _post(self, url, data=None, json=None, **kwargs):
        """
        Sends a POST request. Returns :class:`Response` object.

        :url: URL for the new :class:`Request` object.
        :data: (optional) Dictionary, bytes, or file-like object
            to send in the body of the :class:`Request`.
        :json: (optional) json to send in the body of the :class:`Request`.
        :returns: :class:`requests.Response`
        """
        # return self._session.post(url, data, json, **kwargs)
        responseFromPost = self._session.post(url, data, json, **kwargs)
        return responseFromPost

    def _put(self, url, data=None, json=None, **kwargs):
        """
        Sends a PUT request. Returns :class:`Response` object.

        :url: URL for the new :class:`Request` object.
        :data: (optional) Dictionary, bytes, or file-like object
            to send in the body of the :class:`Request`.
        :json: (optional) json to send in the body of the :class:`Request`.
        :returns: :class:`requests.Response`
        """
        # return self._session.post(url, data, json, **kwargs)
        responseFromPut = self._session.put(url, data, json, **kwargs)
        return responseFromPut


    def _get(self, url, params=None, **kwargs):
        """
        Sends a GET request. Returns :class:`Response` object.

        :url: URL for the new :class:`Request` object.
        :returns: :class:`requests.Response`
        """
        return self._session.get(url, **kwargs)


    def _delete(self, url, params=None, **kwargs):
        """
        Sends a DELETE request. Returns :class:`Response` object.

        :url: URL for the new :class:`Request` object.
        :returns: :class:`requests.Response`
        """
        return self._session.delete(url, **kwargs)



    #===================================================================================================================
    # S N O W   r e l a t e d   m e t h o d s
    #===================================================================================================================

    def getDataFromSnowAPI(self, SNOWAPI='', **kwargs):

        if SNOWAPI == 'getshpmetricconfigdata' or SNOWAPI == 'getshpchangeconfigdata':
            self.debug('API: ' + SNOWAPI)
            SNOWURL = 'https://' + str(self._snowinstance) + '.service-now.com/api/x_sahr_health_port/' + SNOWAPI
            #         'https://sabredev2.service-now.com/api/x_sahr_health_port/getshpchangeconfigdata'
            #                                                                  'getshpchangeconfigdata'
            headers = {"Content-Type":"application/json","Accept":"application/json"}

            self.debug('URL: ' + str(SNOWURL))

            response = requests.get(SNOWURL, auth=(self._snowuser, self._snowpassword), headers=headers )
            # Check for HTTP codes other than 200
            if response.status_code != 200:
                self.debug('#*Cannot get changes info from %s: Status: %s Response: %r' % (self._snowinstance, response.status_code, response.json()))
                raise Exception('Cannot get changes info from %s: '
                                'Status: %s Response: %r' % (self._snowinstance, response.status_code, json.dumps(response.json())))
                exit()
            # Decode the JSON response into a dictionary and use the snowInfo
            self.debug('#Got Info from %s: Status: %s Response: %r' % (self._snowinstance, response.status_code, json.dumps(response.json())))
            snowInfo = response.json()
            self.debug("#ServiceNow " + SNOWAPI + " Info: " + json.dumps(snowInfo))
            return snowInfo

    def getAllFromSnowAPI(self, *args, **kwargs):
        # Decode the JSON response into a dictionary and use the changesInfo
        self.changesInfo = self.getDataFromSnowAPI('getshpchangeconfigdata')
        self.debug('changesInfo: ' + json.dumps(self.changesInfo))
        self.servicesInfo = self.getDataFromSnowAPI('getshpmetricconfigdata')
        self.debug('servicesInfo: ' + json.dumps(self.servicesInfo))

        return { "changesInfo": self.changesInfo, "servicesInfo": self.servicesInfo }


    def getAllFromSnow(self, *args, **kwargs):
        if not os.path.exists(self.CONFIG_FILE_NAME):
            os.system("/opt/aed/shp/bin/download_service_configurations.py")
        self.servicesInfo  = self.load_file(self.CONFIG_FILE_NAME)
        if not os.path.exists(self.CHANGE_FILE_NAME):
            os.system("/opt/aed/shp/bin/download_change_configurations.py")
        self.changesInfo  = self.load_file(self.CHANGE_FILE_NAME)
        return { "changesInfo": self.changesInfo, "servicesInfo": self.servicesInfo }




    #===================================================================================================================
    # G R A F A N A   r e l a t e d   m e t h o d s
    #===================================================================================================================

    def grafanaAPI(self, OPTION='get', API='api/search', DATA=None, **kwargs ):

        if API[0] == '/':
            API = API[1:]
        if API[0:4] != 'api/':
            API = 'api/' + API

        _search_url = os.path.join(self.URL,API)
        _char = '?'
        _pOrgId = kwargs.get('ORGID')
        if _pOrgId:
            _orgId, _orgName = self.findOrg(_pOrgId)
            if _orgId > 0:
                _search_url = _search_url + _char + 'orgId=' + str(_orgId)
                _char = '&'

        for keyword in ['from','to','dashboardId','limit','panelId','type','tags']:
            _parm = kwargs.get(keyword.upper())
            if _parm:
                _search_url = _search_url + _char + keyword + '=' + str(_parm)
                _char = '&'
   

        self.debug("#grafanaAPI URL: " + _search_url)

        _headers = {"Content-Type": "application/json", "Accept": "application/json"}

        _maxTries = 2
        if self.MAXTRIES < 5:
            _maxTries = self.MAXTRIES

        for _try in range(1,_maxTries + 1):
            try:
                _search = getattr(self, '_' + OPTION)(_search_url, DATA, auth=(self._user, self._password), headers=_headers, timeout=(5.0, 10.0))
                break

            except requests.ConnectionError as CONERR:
                print("**** TIMEOUT *****")
                print("CONN TRY # {0} : {1}".format(_try, CONERR.message))
                if _try == _maxTries:
                    raise

        if _search.status_code != 200:
            self.debug(
                'Cannot %s %s: Status: %s Response: %r'.format(OPTION, API, _search.status_code, json.dumps(_search.json())))
            raise Exception(
                'Cannot %s %s: Status: %s Response: %r'.format(OPTION, API, _search.status_code, json.dumps(_search.json())))

        # Decode the JSON response into a dictionary and use the changesInfo
        return _search.json()

    def findOrg(self, ORG=None):

        self.debug("#findOrg Looking for ORG " + str(ORG) + " from self.orgs_dict " + json.dumps(self.orgs_dict))

        _orgFound = False

        if str(ORG).isdigit():
            _orgId   = ORG
            _orgName = self.getOrgName(_orgId)
            _orgFound = (_orgName != None)
        else:
            _orgName = ORG
            _orgId   = self.getOrgId(_orgName)
            _orgfound = (_orgId > 0)

        if not _orgFound:
            _orgId   = 0
            self.debug("#findOrg ORG={0} Was Not Found".format(ORG))

        return _orgId, _orgName

    def getOrgs(self, *args, **kwargs):
        # self.orgs = self.grafanaAPI('get', '/api/orgs')
        # self.grafanaAPI method needs to get current organisation, so
        # don't call grafanaAPI to avoid recursive calls

        _search_url = self.URL + '/api/orgs'
        _headers = {"Content-Type": "application/json", "Accept": "application/json"}
        _search = self._get(_search_url,
                            auth=(self._user, self._password),
                            headers=_headers
                            )
        self.orgs = _search.json()
        if _search.status_code != 200:
            self.debug(
                'Cannot %s %s: Status: %s Response: %r'.format('GET', _search_url, _search.status_code, json.dumps(_search.json())))
            raise Exception(
                'Cannot %s %s: Status: %s Response: %r'.format('GET', _search_url, _search.status_code, json.dumps(_search.json())))
            exit()

        # Build the dictionary
        # [{"id": 1, "name": "Main Org."}, {"id": 2, "name": "Staging"}]

        # {"orgs": [{"id": 1, "name": "Main Org."}, {"id": 2, "name": "Staging"}],
        #  "2": "Staging",
        #  "Main Org.": 1,
        #  "Staging": 2,
        #  "1": "Main Org."
        # }

        self.orgs_dict = {"orgs": self.orgs}
        for org in self.orgs:
            _oname = org["name"]
            _oid = org["id"]
            # self.debug("#ORG %d %s" % (_oid, _oname))

            self.orgs_dict[_oname] = _oid
            self.orgs_dict[_oid] = _oname

        # self.debug("Grafana Orgs indexed: " + json.dumps(self.orgs_dict))
        return self.orgs_dict

    def getCurrentOrg(self):
        return self.current_org

    def getGrafanaCurrentOrg(self):
        #self.current_org = self.grafanaAPI('get', '/api/org/')
        # self.grafanaAPI method needs to get current organisation, so
        # don't call grafanaAPI to avoid recursive calls
        _search_url = self.URL + '/api/org/'
        _search = self._get(_search_url,
                            auth=(self._user, self._password),
                            headers={"Content-Type": "application/json", "Accept": "application/json"}
                           )
        if _search.status_code != 200:
            self.debug(
                'Cannot %s %s: Status: %s Response: %r'.format('GET', _search_url, _search.status_code, json.dumps(_search.json())))
            raise Exception(
                'Cannot %s %s: Status: %s Response: %r'.format('GET', _search_url, _search.status_code, json.dumps(_search.json())))
            exit()

        self.current_org = _search.json()
        return self.current_org

    def getOrgName(self,ORGID):
        _orgName = None
        if str(ORGID).isdigit():
            _orgName = self.orgs_dict.get(int(str(ORGID)))

        return _orgName


    def getOrgId(self, ORGNAME):
        _orgId = 0

        if ORGNAME:
            if not str(ORGNAME).isdigit():
                _orgId = self.orgs_dict.get(str(ORGNAME))
                if _orgId == None:
                    _orgId = 0
        return _orgId

    def setCurrentOrg(self, ORG='Main Org.'):

        _orgId, _orgName = self.findOrg(ORG)
        _orgFound = (_orgId > 0)

        self.debug("#setOrg ID={0} NAME={1}".format(_orgId, _orgName))


        #_orgObj   = {"name": _orgName}
        _response = self.grafanaAPI('post', 'api/user/using/' + str(_orgId) )
        self.debug("#Grafana response from set current org: " + json.dumps(_response))
        self.current_org = self.getGrafanaCurrentOrg()

        self.debug("#Grafana Current Org after setCurrentOrg: " + json.dumps(self.current_org))
        return self.current_org


    def addOrg(self, ORG='Staging'):

        _orgId, _orgName = self.findOrg(ORG)
        _orgFound = (_orgId > 0)

        self.debug("#setOrg ID={0} NAME={1}".format(_orgId, _orgName))

        if not _orgFound:
            _orgObj   = {"name": _orgName}
            _response = self.grafanaAPI('post', 'orgs', json.dumps(_orgObj) )
            self.debug("#Grafana response from add org: " + json.dumps(_response))
            self.orgs_dict   = self.getOrgs()               # Update the dictionary
            #Don't let it change current org
            #self.current_org = self.getGrafanaCurrentOrg() # Update current to grafana's
            #restore current org to previous before ADD
            self.setCurrentOrg(ORG=self.current_org.get('name')) # Re-set org to previous one
            self.debug("#addOrg: CURRENT ORG AFTER ADD: " + json.dumps(self.current_org))
            self.debug("#addOrg:    ORG DICT AFTER ADD: " + json.dumps(self.orgs_dict))
        else:
            self.debug("#addOrg: Grafana org already exists: {0} : {1}".format(_orgId, _orgName))
            raise Exception("#addOrg: Grafana org already exists: {0} : {1}".format(_orgId, _orgName))

        self.debug("#Grafana Current Org after setCurrentOrg: " + json.dumps(self.current_org))
        return self.current_org


    def deleteOrg(self, ORG):

        self.orgs_dict = self.getOrgs()   # Update Organizations Dictionary
        _orgId, _orgName = self.findOrg(ORG)
        _orgFound = (_orgId > 0)

        self.debug("#deleteOrg ID={0} NAME={1}".format(_orgId, _orgName))

        if _orgId > 0:
            _response = self.grafanaAPI('delete','orgs/' + str(_orgId))
            self.orgs_dict = self.getOrgs() # Update orgs dictionary
            return _response
        else:
            self.debug("#Organization %s \"%s\" not found: %s".format(str(_orgId), _orgName, json.dumps(self.orgs_dict)) )
            return self.orgs_dict


    #---------------------------------------
    def invalidMethod(self,*args,**kwargs):
        self.debug(
            'Invalid method name called on grafanaAPI: %s '.format(args[0])
        )
        raise Exception(
            'Invalid method name called on grafanaAPI: %s '.format(args[0])
        )

    def getPanels(self, dashboardUid, _orgId):
        _dashboardItem = self.grafanaAPI('get', 'dashboards/uid/' + dashboardUid, ORGID=_orgId)
        _panels = []
        _dashboardEntry = _dashboardItem.get('dashboard')
        if _dashboardEntry:
            _dashboardPanels = _dashboardEntry.get('panels')
            if _dashboardPanels:
                for _panelObj in _dashboardPanels:
                    _panel = { "id": _panelObj['id']}
                    _panels.append(_panel)

        return _panels

    def getDashboards(self, *args, **kwargs):
        _orgId = kwargs.get('ORGID')
        if not _orgId:
            _orgId = self.current_org['id']

        _dashboards = self.grafanaAPI('get','/api/search', ORGID=_orgId)
        self.debug("#Dashboards from Local Grafana: " + json.dumps(_dashboards))

        #self.debug("#Replacing Dashboards with test data...")
        # TESTFILENAME = './examples/dashboardsDEV.json'
        # dashboardInfo = load_file(TESTFILENAME)
        # debug("#Dashboards from Testdata from Grafana: " + json.dumps(dashboardInfo))

        # Build table of dashboardsID per UUID
        self.dashboardDict = { "dashboards": _dashboards }

        for _dash in _dashboards:
            _uid = _dash['uid']
            _id  = _dash['id']
            _panels = self.getPanels(_uid, _orgId)
            _dictEntry = { "uid": _uid, "id": _id, "panels": _panels }
            self.dashboardDict[_uid] = _dictEntry
            self.dashboardDict[_id]  = _dictEntry
        self.debug("#Dashboard dictionary: " + json.dumps(self.dashboardDict))

        return self.dashboardDict



    # ===================================================================================================================
    # A N N O T A T I O N S   R E L A T E D   M E T H O D S
    # ===================================================================================================================

    def loadAnnotation(self,_annt, annotations, **kwargs):
        self.debug("#loadAnnotations> Annotation From Grafana: " + json.dumps(_annt))

        _HASH = kwargs.get('HASH')
        if not _HASH:
            _HASH = getattr(self, "parseSysId")


        _hash = _HASH(_annt)

        if _hash:
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

            if not annotations.get(_homerange):
                annotations[_homerange] = []  # Make the group be a list of ranges object

            _region = next((x for x in annotations[_homerange] if x.get('regionId') == _regionId), None)

            if not _region:
                _region = {"regionId": _regionId, "annotations": []}
                annotations[_homerange].append(_region)

            _region['annotations'].insert(0, _annotation)

            return annotations

    def getRangeList(self, annotations, dashboardId, panelId, hash):
        _regionlist = []
        _homerange = (dashboardId, panelId, hash)
        _regions   = annotations.get(_homerange)
        if _regions:
            _regionlist = [_region['regionId'] for _region in _regions]

        return _regionlist

    def printAnnotations(self,annotations):
        for _homerange in list(annotations.keys()):
            print("#getAnnotations> _homerange=" + str(_homerange))
            d, p, h = _homerange
            _regionlist = [_region['regionId'] for _region in annotations[_homerange]]

            print("Region list for {0} = {1}".format(_homerange, _regionlist))

            for _region in annotations[(d, p, h)]:
                _regionId  = _region['regionId']
                _rangeList = _region['annotations']
                _c = 0
                for _ann in _rangeList:
                    print("#    DASH=%d PANEL=%d HASH='%s' REGION=%s [%2d]: \t %s".format
                          (d, p, h, _region, _c, json.dumps(_ann))
                          )
                    _c = _c + 1

    def getAnnotations(self, *args, **kwargs):
        _orgId = kwargs.get('ORGID')
        if not _orgId:
            _orgId = self.current_org['id']

        _HASH = kwargs.get('HASH')
        if not _HASH:
            _HASH = getattr(self, "parseSysId")

        _annotations = []
        _dashboardId = kwargs.get('DASHBOARDID')
        _limit       = kwargs.get('LIMIT')
        if not _limit:
            _limit = 100
        _limit       = kwargs.get('LIMIT')

        if not _limit:
            _limit = 100

        if _dashboardId:
            _annotations = self.grafanaAPI('get','annotations', ORGID=_orgId, LIMIT=_limit, TYPE='annotation', DASHBOARDID=_dashboardId)
        else:
            _annotations = self.grafanaAPI('get','annotations', ORGID=_orgId, LIMIT=_limit, TYPE='annotation')

        self.annotations = { }
        self.debug("#getAnnotations: annotations object = " + json.dumps(_annotations))
        for _annt in _annotations:
            self.debug("#getAnnotations> Annotation From Grafana: " + json.dumps(_annt))
            self.annotations = self.loadAnnotation(_annt, self.annotations, HASH=_HASH)


        if self.VERBOSE or self.DEBUG:
            self.printAnnotations(self.annotations)

        return self.annotations


    def makeAnnotationsForServices(self, *args, **kwargs):
        #
        # Start matching changes with panels from change's cmdb_ci
        # and create annotations requests
        #

        annotationsReqs = {}  # By Dashboard ID

        allSnowInfo   = self.getAllFromSnow()
        changesInfo   = allSnowInfo['changesInfo']
        servicesInfo  = allSnowInfo['servicesInfo']
        dashboardDict = self.getDashboards(*args, **kwargs)

        apiVersionNumber = changesInfo['result'].get('thisapiversion', 1)
        newApiVersion    = (apiVersionNumber > 1)

        changedServicesList = []
        if newApiVersion:
            changedServicesList = [changesInfo['result']['services'][service]['name']
                                   for service in
                                   list(changesInfo['result']['services'].keys())]
        else:
            changedServicesList = [service for service in list(changesInfo['result']['services'].keys())]

        self.debug("#Changed Services List: " + str(changedServicesList))

        for service in changedServicesList:
            self.debug("#Service = " + service)
            serviceEntry = servicesInfo['result']['services'].get(service)
            self.debug("#Service Entry: " + json.dumps(serviceEntry))

            if serviceEntry:
                serviceUID = serviceEntry['uid']
                # Look for the service UID on dashboards
                if serviceUID in dashboardDict:
                    dashboardID = dashboardDict[serviceUID]['id']
                    self.debug("#Found on dict dashboard UID {0} = {1}".format(serviceUID, dashboardID))
                else:
                    dashboardID = 0
                    _curr = self.current_org
                    _orgId = _curr['id']
                    _orgName = _curr['name']
                    self.debug("#No Dashboard UID {0} found on ORG {1} {2}".format(serviceUID, _orgId, _orgName))

                if dashboardID > 0:
                    if not annotationsReqs.get(dashboardID):
                        annotationsReqs[dashboardID] = []  # Initialize annotations for that dashboard ID

                    _panels = self.dashboardDict[serviceUID]['panels']
                    self.debug("#Panels List: " + str(_panels))
                    for _panel in _panels:
                        _panel_id = _panel['id']
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
                            _annotation_end   = int(str(int(change['end_datetime']  )) + '000')

                            _work_start_datetime = int(change.get('work_start_datetime'))
                            _work_end_datetime = int(change.get('work_end_datetime'))

                            if _work_start_datetime > 0:
                                _annotation_start = int( str(_work_start_datetime) + '000')

                            if _work_end_datetime > 0:
                                _annotation_end = int( str(_work_end_datetime) + '000')

                            _annotationReq = self.annotationRequest(
                                DASHBOARD=dashboardID,
                                PANEL=_panel_id,
                                TIME   =_annotation_start,
                                ENDTIME=_annotation_end,
                                TAGS=[],  #[change['number']],
                                TEXT="<a target=\"_blank\" href='https://" + changesInfo['result']['instancename'] +
                                        ".service-now.com/nav_to.do?uri=change_request.do?sys_id=" +
                                        change['sys_id'] + "'>" +
                                        change['number'] +
                                        "</a>" +
                                        ": " + change['short_description']
                            )

                            self.debug("#makeAnnotationsForServices> Annotation: " + json.dumps(_annotationReq))
                            annotationsReqs[dashboardID].append(_annotationReq)

                else:
                    self.debug("#makeAnnotationsForServices> No panels for service " + service)
            else:
                self.debug("#makeAnnotationsForServices> Service " + service + ' Not Found.')

        # ================================================================
        self.debug("#makeAnnotationsForServices> annotationReqs: " + json.dumps(annotationsReqs))
        return annotationsReqs


    def createAnnotation(self,annotationRequest, **kwargs):
        _orgId = kwargs.get('ORGID')
        if not _orgId:
            _orgId = self.current_org['id']

        try:
            _createResponse = self.grafanaAPI('post','annotations',DATA=json.dumps(annotationRequest), ORGID=_orgId)
        except Exception as E:
            self.debug("#createAnnotation> Exception: " + str(E.message))
            raise

        self.debug("#addAnnotation> add Response = " + json.dumps(_createResponse))

        return _createResponse

    def deleteAnnotation(self, annotationId, **kwargs):
        _orgId = kwargs.get('ORGID')
        if not _orgId:
            _orgId = self.current_org['id']

        _deleteResponse = self.grafanaAPI('delete', 'annotations/' + str(annotationId), ORGID=_orgId)

        self.debug("#deleteAnnotation> delete Response = " + json.dumps(_deleteResponse))

        return _deleteResponse

    def deleteAnnotationRange(self, regionId, **kwargs):
        _orgId = kwargs.get('ORGID')
        if not _orgId:
            _orgId = self.current_org['id']

        try:
            _deleteResponse = self.grafanaAPI('delete', 'annotations/region/' + str(regionId), ORGID=_orgId)
        except Exception as E:
            self.debug("#deleteAnnotationRange: Exception: " + E.message)
            raise

        self.debug("#deleteAnnotation> delete Response = " + json.dumps(_deleteResponse))

        return _deleteResponse


    #===================================================================================================================
    # S S O   M E T H O D S .   F o r   f u t u r e   a l t e r n a t e   s i g n o n
    #===================================================================================================================
    # @property
    # def cookies(self):
    #     """Access cookies stored in :class:`requests.Session` object instance.
    #
    #     :returns: :class:`cookielib.CookieJar` but exposes a dict interface.
    #     """
    #     return self._session.cookies
    #
    # def server_info(self):
    #     """Makes GET request to obtain serverinfo.
    #
    #     :returns: :class:`requests.Response`
    #     """
    #     url = os.path.join(self.SSO_MAIN, 'serverinfo/*')
    #     return self._sso_get(url)
    #
    # def acquire_token(self, username, password):
    #     """Make POST request to authenticate user to OpenAM
    #     and get authorization token.
    #     If given credentials are invalid Exception is raised.
    #
    #     :username: string
    #     :password: string
    #     :returns: string
    #     """
    #     url = os.path.join(self.SSO_MAIN, 'authenticate')
    #     headers = {
    #         "X-OpenAM-Username": username,
    #         "X-OpenAM-Password": password
    #     }
    #     response = self._post(url, auth=(username, password), headers=headers)
    #
    #     try:
    #         data = response.json()
    #         return data['tokenId']
    #     except ValueError as exc:
    #         raise exc
    #     except KeyError:
    #         raise Exception('Cannon authenticate user, '
    #                         'response does not contain requested token.'
    #                         'Response: %r' % response.json())
    #
    # def authenticate(self, username = '', password = ''):
    #     """Automatically obtain token based on cookie's name
    #     that is returned by `server_info`
    #
    #     :username: string
    #     :password: string
    #     """
    #
    #     if username == '':
    #         username = self._snowuser
    #
    #     if password == '':
    #         password = self._snowpassword
    #
    #     try:
    #         response = self.server_info().json()
    #     except ValueError:
    #         raise Exception('Response does not contain valid JSON')
    #     else:
    #         token = self.acquire_token(username, password)
    #         cookie = response.get('cookieName', 'wamIntInternalSabreCookie')
    #         self.cookies[cookie] = token
    #         return True
