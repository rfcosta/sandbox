class Customer:

    def __init__(self, service, customer_code, customer_name, customer_sys_id):
        self.state = service.state
        if self.state != 'validated':
            self.state = 'staging-no-alerting'
        self.panels = []
        self.name = str(customer_name)
        self.code = str(customer_code)
        self.sys_id = str(customer_sys_id)
        self.knowledge_article = ""
        self.report_grouping = 'Customers'
        self.dashboard_uid = self.get_dashboard_uid()

    def get_dashboard_uid(self):
        if self.sys_id != 'None':
            return self.sys_id
        return self.code + self.state   # backwards compatibility

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

    def add_panel(self, panel):
        self.panels.append(panel)

    def __str__(self):
        s = ("Customer Name:   " + self.name.encode('ascii', 'ignore') + '\n' +
             "  Customer Code:   " + self.code.encode('ascii', 'ignore') + '\n' +
             "  Customer Sys ID: " + self.sys_id.encode('ascii', 'ignore') + '\n' +
             "  state:           " + self.state + '\n' +
             "  dashboard uid:   " + self.dashboard_uid + '\n' +
             "  kb article:      " + self.knowledge_article + '\n' +
             "  report grouping: " + self.report_grouping) + '\n'
        for panel in self.panels:
            s = s + str(panel) + '\n'
        return s
