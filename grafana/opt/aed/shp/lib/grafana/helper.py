import sys
import json
import requests
import traceback
from requests.auth import HTTPBasicAuth

sys.path.append( '/opt/aed/shp/lib')
sys.path.append( '/opt/aed/shp/lib/grafana')

import shputil

class Helper():

  def __init__(self):
    self.base_url = shputil.get_grafana_base_api_url()
    self.config = shputil.get_config()
    self.credentials = shputil.get_grafana_credentials()


  def switch_org(self,org_id):
    self.api_post("user/using/" + str(org_id))


  def api_delete(self, function):
    headers = {'content-type': 'application/json'}
    resp = requests.delete(self.base_url + function, auth=self.credentials, headers=headers)
    if resp.status_code != 200:
      raise IOError("Error in api_delete for function: " + function + " - " + resp.text)
    return resp


  def api_get(self, function):
    headers = {'content-type': 'application/json'}
    resp = requests.get(self.base_url + function, auth=self.credentials, headers=headers)
    if resp.status_code != 200:
      raise IOError("Error in api_get for function: " + function + " - " + resp.text)
    return resp


  def api_get_with_params(self, function, params):
    headers = {'content-type': 'application/json'}
    resp = requests.get(self.base_url + function, params=params, auth=self.credentials, headers=headers)
    if resp.status_code != 200:
      raise IOError("Error in api_get_with_params for function: " + function + " - " + resp.text)
    return resp


  def api_post(self, function):
    headers = {'content-type': 'application/json'}

    resp = requests.post(self.base_url + function, auth=self.credentials, headers=headers)
    if resp.status_code != 200:
      raise IOError("Error in api_post for function: " + function + " - " + resp.text)
    return resp


  def api_post_with_data(self, function, payload):
    headers = {'content-type': 'application/json'}

    resp = requests.post(self.base_url + function, data=json.dumps(payload), auth=self.credentials, headers=headers)

    if resp.status_code != 200:
      #print("Payload: '" + self.base_url + function + "' "  + json.dumps(payload, indent=4) )
      #print "Error in api_post_with_data for function: " + function + " - " + resp.text
      raise IOError("Error in api_post_with_data for function: " + function + " - " + resp.text)
    return resp
