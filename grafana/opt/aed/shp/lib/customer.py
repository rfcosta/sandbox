from panel import Panel


class Customer():

    def __init__(self, service, customer_code, customer_name):
        self.state = service.state
        if self.state != 'validated':
            self.state = 'staging-no-alerting'
        self.panels = []
        self.name = str(customer_name)
        self.code = str(customer_code)
        self.knowledge_article = ""
        self.report_grouping = 'Customers'
        self.dashboard_uid = self.get_dashboard_uid()

    def get_dashboard_uid(self):
        return self.code + ":" + self.state

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
        s = ("Customer Name: " + self.name.encode('ascii', 'ignore') + '\n' +
             "  Code:            " + self.code.encode('ascii', 'ignore') + '\n' +
             "  state:           " + self.state + '\n' +
             "  dashboard uid:   " + self.dashboard_uid + '\n' +
             "  kb article:      " + self.knowledge_article + '\n' +
             "  report grouping: " + self.report_grouping) + '\n'
        for panel in self.panels:
            s = s + str(panel) + '\n'
        return s
