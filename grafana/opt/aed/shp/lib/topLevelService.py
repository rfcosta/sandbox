from child import Child

class TopLevelService():
    def __init__(self, topLevelService):
        self.children = []
        self.name = topLevelService['name'] if 'name' in topLevelService else 'General'
        self.report_grouping = topLevelService['reporting_group'] if 'reporting_group' in topLevelService else 'General'
        self.load_children(topLevelService)
        self.dashboard_uid = self.get_dashboard_uid(topLevelService)

    def get_dashboard_uid(self, topLevelService):
        if 'sys_id' in topLevelService and topLevelService['sys_id'] != 'undefined':
            dashboard_uid = "AGG_" + topLevelService['sys_id']
        return dashboard_uid.encode('ascii', 'ignore')

    def load_children(self, topLevelService):
        children = topLevelService['children']
        for child in children:
            my_child = Child(child)
            self.children.append(my_child)


    def __str__(self):
        s = ("Top Level Service Name: " + self.name.encode('ascii', 'ignore') + '\n' +
             "  dashboard uid:        " + self.dashboard_uid + '\n' +
             "  report grouping:      " + self.report_grouping) + '\n'
        for child in self.children:
            s = s + str(child) + '\n'
        return s
