import sys
import json
import requests
from retrying import retry

sys.path.append('/opt/aed/shp/lib')
sys.path.append('/opt/aed/shp/lib/grafana')

import shputil


class Helper:

    def __init__(self, org_id):
        self.org_id = str(org_id)
        self.base_url = shputil.get_grafana_base_api_url()
        self.config = shputil.get_config()
        self.credentials = shputil.get_grafana_credentials()

    @retry(stop_max_delay=10000, wait_fixed=2000)
    def switch_org(self, org_id):
        self.api_post("user/using/" + str(org_id))

    @retry(stop_max_delay=10000, wait_fixed=2000)
    def api_get_with_params(self, function, params):
        headers = {'content-type': 'application/json', 'X-Grafana-Org-Id': str(self.org_id)}
        url = self.base_url + function
        resp = requests.get(url, params=params, auth=self.credentials, headers=headers)
        if resp.status_code != 200:
            print("Failed: ", resp)
            raise IOError("Error in api_get_with_params for function: " + function + " - " + resp.text)
        return resp

    @retry(stop_max_delay=10000, wait_fixed=2000)
    def api_delete(self, function):
        headers = {'content-type': 'application/json', 'X-Grafana-Org-Id': str(self.org_id)}
        url = self.base_url + function
        resp = requests.delete(url, auth=self.credentials, headers=headers)
        if resp.status_code != 200:
            print("Failed: ", resp)
            raise IOError("Error in api_delete for function: " + function + " - " + resp.text)
        return resp

    @retry(stop_max_delay=10000, wait_fixed=2000)
    def api_post(self, function):
        headers = {'content-type': 'application/json', 'X-Grafana-Org-Id': str(self.org_id)}

        url = self.base_url + function
        resp = requests.post(url, auth=self.credentials, headers=headers)
        if resp.status_code != 200:
            print("Failed: ", resp)
            raise IOError("Error in api_post for function: " + function + " - " + resp.text)
        return resp

    @retry(stop_max_delay=10000, wait_fixed=2000)
    def api_post_with_data(self, function, payload):
        headers = {'content-type': 'application/json', 'X-Grafana-Org-Id': str(self.org_id)}

        url = self.base_url + function
        resp = requests.post(url, data=json.dumps(payload), auth=self.credentials, headers=headers)
        if resp.status_code != 200:
            print("Failed: ", resp)
            raise IOError("Error in api_post_with_data: " + function + " - " + payload + " - " + resp.text)
        else:
            print("Success")

        return resp

    @retry(stop_max_delay=10000, wait_fixed=2000)
    def api_patch_with_data(self, function, payload):
        headers = {'content-type': 'application/json', 'X-Grafana-Org-Id': str(self.org_id)}

        url = self.base_url + function
        resp = requests.patch(url, data=json.dumps(payload), auth=self.credentials, headers=headers)
        if resp.status_code != 200:
            print("Failed: ", resp)
            raise IOError("Error in api_patch_with_data: " + function + " - " + resp.text)

        return resp

    @retry(stop_max_delay=10000, wait_fixed=2000)
    def api_put_with_data(self, function, payload):
        headers = {'content-type': 'application/json', 'X-Grafana-Org-Id': str(self.org_id)}

        url = self.base_url + function
        resp = requests.put(url, data=json.dumps(payload), auth=self.credentials, headers=headers)
        if resp.status_code != 200:
            print("Failed: ", resp)
            raise IOError("Error in api_put_with_data: " + function + " - " + resp.text)

        return resp
