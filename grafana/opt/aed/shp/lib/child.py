class Child():
    def __init__(self, child):
        self.name = child['name'] if 'name' in child else ''
        self.sys_id = child['sys_id'] if 'sys_id' in child else ''
        self.report_grouping = child['reporting_group'] if 'reporting_group' in child else ''

    def __str__(self):
        s = ("    Child Name:        " + self.name.encode('ascii', 'ignore') + '\n' +
             "      sys_id:          " + self.sys_id + '\n' +
             "      report grouping: " + self.report_grouping) + '\n'
        return s
