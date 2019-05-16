import sys
import requests
import json
import logging

sys.path.append( '/opt/aed/shp/lib')
sys.path.append( '/opt/aed/shp/lib/grafana')

import shputil

from helper import Helper

class Dashboards():


  def __init__(self, org_id):
    self.org_id = org_id
    self.dashboards = dict()
    self.helper = Helper(org_id)
    self.load_all()


  def add_dashboard_to_list(self, dashboard):
    self.dashboards[dashboard['uid']] = dashboard['title']


  def load_all(self):
    resp = self.helper.api_get_with_params("search", { 'type': 'dash-db' })
    dashboards = json.loads(resp.content)
    for dashboard in dashboards:
      self.add_dashboard_to_list(dashboard)


  def get_dashboards(self):
    return self.dashboards


  def create_dashboard(self, uid, json):
    print "Creating dashboard: " + uid
    id = self.helper.api_post_with_data('dashboards/db', json)
    return id


  def delete_dashboard(self, uid):
    print "Deleting dashboard: " + uid
    resp = self.helper.api_delete('dashboards/uid/' + uid)
