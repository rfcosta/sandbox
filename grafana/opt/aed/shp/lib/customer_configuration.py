import json
import sys
import copy

from service_configuration import ServiceConfiguration
from customer import Customer

sys.path.append('/opt/aed/shp/lib')

class CustomerConfiguration():

    @staticmethod
    def sortable_names(x):
        return x.name


    @staticmethod
    def sortable_customers(x):
        return x.name


    def __init__(self, service_configuration, all='ALL'):

        self.all = all.upper()
        self.customers = []
        self.customers_db = dict()
        self.services_list = service_configuration.get_services()
        self.sortedServices = sorted(self.services_list, key=self.sortable_names)

        for service in self.sortedServices:

            for panel in service.panels:
                _customer_code = str(panel.customer_code).upper()
                if _customer_code == self.all:
                    continue

                _customer_name = str(panel.customer_name)
                _customer = Customer(service, _customer_code, _customer_name)

                self.customers_db.setdefault(_customer.dashboard_uid, _customer)

                _panel_copy = copy.deepcopy(panel)
                self.customers_db[_customer.dashboard_uid].add_panel(_panel_copy)

        for _cust_uid in self.customers_db:
            _customer = self.customers_db[_cust_uid]
            self.customers.append(_customer)

    def get_customers(self):
        return sorted(self.customers, key=self.sortable_customers)


# For unit test purposes
if __name__ == '__main__':
    service_configuration = ServiceConfiguration()
    cust = CustomerConfiguration(service_configuration)

    customers_list = cust.get_customers()

    for customer in customers_list:
        print(str(customer))
