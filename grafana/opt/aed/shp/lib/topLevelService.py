from child import Child


class TopLevelService:


    def __init__(self, top_level_service):
        self.children = []
        self.name = top_level_service['name'] if 'name' in top_level_service else 'General'
        self.report_grouping = top_level_service['reporting_group'] if 'reporting_group' in top_level_service else 'General'
        self.load_children(top_level_service)
        self.dashboard_uid = self.get_dashboard_uid(top_level_service)


    def get_dashboard_uid(self, top_level_service):
        if 'sys_id' in top_level_service and top_level_service['sys_id'] != 'undefined':
            dashboard_uid = "AGG_" + top_level_service['sys_id']
        return dashboard_uid.encode('ascii', 'ignore')


    def load_children(self, top_level_service):
        children = top_level_service['children']
        for child in children:
            my_child = Child(child)
            self.children.append(my_child)

    def __str__(self):
        s = ("Top Level Service Name: " + str(self.name.encode('ascii', 'ignore')) + '\n' +
             "  dashboard uid:        " + self.dashboard_uid + '\n' +
             "  report grouping:      " + self.report_grouping) + '\n'
        for child in self.children:
            s = s + str(child) + '\n'
        return s
