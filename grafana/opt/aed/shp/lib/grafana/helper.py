import sys
import json
import logging
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
    def api_get_with_params(self, function, params):
        headers = {'content-type': 'application/json', 'X-Grafana-Org-Id': str(self.org_id)}
        url = self.base_url + function
        resp = requests.get(url, params=params, auth=self.credentials, headers=headers)
        try:
            if not resp.ok:
                resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.exception(e)
        return resp

    @retry(stop_max_delay=10000, wait_fixed=2000)
    def api_delete(self, function):
        headers = {'content-type': 'application/json', 'X-Grafana-Org-Id': str(self.org_id)}
        url = self.base_url + function
        resp = requests.delete(url, auth=self.credentials, headers=headers)
        try:
            if not resp.ok:
                resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.exception(e)
        return resp

    @retry(stop_max_delay=10000, wait_fixed=2000)
    def api_post(self, function):
        headers = {'content-type': 'application/json', 'X-Grafana-Org-Id': str(self.org_id)}

        url = self.base_url + function
        resp = requests.post(url, auth=self.credentials, headers=headers)
        try:
            if not resp.ok:
                resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.exception(e)
        return resp

    @retry(stop_max_delay=10000, wait_fixed=2000)
    def api_post_with_data(self, function, payload):
        headers = {'content-type': 'application/json', 'X-Grafana-Org-Id': str(self.org_id)}
        url = self.base_url + function
        resp = requests.post(url, data=json.dumps(payload), auth=self.credentials, headers=headers)
        try:
            if not resp.ok:
                resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.exception(e)
        return resp

    @retry(stop_max_delay=10000, wait_fixed=2000)
    def api_patch_with_data(self, function, payload):
        headers = {'content-type': 'application/json', 'X-Grafana-Org-Id': str(self.org_id)}
        url = self.base_url + function
        resp = requests.patch(url, data=json.dumps(payload), auth=self.credentials, headers=headers)
        try:
            if not resp.ok:
                resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.exception(e)
        return resp

    @retry(stop_max_delay=10000, wait_fixed=2000)
    def api_put_with_data(self, function, payload):
        headers = {'content-type': 'application/json', 'X-Grafana-Org-Id': str(self.org_id)}
        url = self.base_url + function
        resp = requests.put(url, data=json.dumps(payload), auth=self.credentials, headers=headers)
        try:
            if not resp.ok:
                resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.exception(e)
        return resp
