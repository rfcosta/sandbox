from panel import Panel

class Service():

  def __init__(self, service_name, service, use_configured_panelIDs):
    self.panels = []
    self.name = service_name
    self.state = service['state']
    self.knowledge_article = service['knowledge_article']
    self.report_grouping = service['report_grouping'] if 'report_grouping' in service else 'General'
    self.load_panels(service, use_configured_panelIDs)
    self.dashboard_uid = self.get_dashboard_uid(service_name, service)

  def get_dashboard_uid(self, service_name, service):
    if 'uid' in service and service['uid'] != 'undefined':
       return service['uid']
    else:
      # convert special characters
      dashboard_uid = self.name.replace(" -", "-")
      dashboard_uid = dashboard_uid.replace("- ", "-")
      dashboard_uid = dashboard_uid.replace("_", "-")
      dashboard_uid = dashboard_uid.replace(" ", "-")
      return dashboard_uid.encode('ascii', 'ignore')

  def load_panels(self, service, use_configured_panelIDs):
    panels = service['panels']
    for panel in panels:
      my_panel = Panel(panels[panel], panel, use_configured_panelIDs)
      self.panels.append(my_panel)
    self.panels.sort(key=lambda x: int(x.panel_id))

  def is_validated(self):
    if self.state == 'validated':
       return True
    return False

  def is_alerting(self):
    if self.state == 'validated':
       return True
    if self.state == 'staging-alerting':
       return True
    return False

  def __str__(self):
    s = ("Service Name: " + self.name.encode('ascii','ignore') + '\n' +
         "  state:           " + self.state + '\n' +
         "  dashboard uid:   " + self.dashboard_uid + '\n' +
         "  kb article:      " + self.knowledge_article + '\n' +
         "  report grouping: " + self.report_grouping) + '\n'
    for panel in self.panels:
      s = s + str(panel) + '\n'
    return s
