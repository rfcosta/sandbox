import json
import sys
import copy

from operator import itemgetter
from service_configuration import ServiceConfiguration

sys.path.append('/opt/aed/shp/lib')

class CustomerConfiguration():

    @staticmethod
    def sortable_names(x):
        return x.name

    def __init__(self, service_configuration, all='ALL'):

        self.all = all.upper()
        self.customers = dict()
        self.services_list = service_configuration.get_services()
        self.sortedServices = sorted(self.services_list, key=self.sortable_names)

        for service in self.sortedServices:

            for panel in service.panels:
                _customer_code = str(panel.customer_code).upper()
                if _customer_code == self.all:
                    continue

                _customer_name = str(panel.customer_name)
                _dashboard_entry = dict(
                    panels              = [],
                    dashboard_uid       = _customer_code,
                    name                = _customer_name,
                    state               = service.state,
                    knowledge_article   = "",
                    report_grouping     = "Customers"
                )

                self.customers.setdefault(_customer_code, _dashboard_entry)

                _panel_entry = copy.deepcopy(panel)
                self.customers[_customer_code]['panels'].append(_panel_entry)

    def get_customers(self):
        return sorted(self.customers, key=self.sortable_names)




if __name__ == '__main__':
    service_configuration = ServiceConfiguration()
    cust = CustomerConfiguration(service_configuration)
