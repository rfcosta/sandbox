#!/bin/env python

import json
import logging
import sys
import copy
import re

import requests

try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote    # Python3


sys.path.append('/opt/aed/shp/lib')
sys.path.append('/opt/aed/shp/lib/grafana')

import shputil
from service_configuration import ServiceConfiguration
from customer_configuration import CustomerConfiguration
from folders import Folders
from dashboards import Dashboards
from helper import Helper

sysidOK = re.compile('^[0-9A-Fa-f]{32,32}$')

columns = 3

folders = {}
dashboards = {}

used_folders = {}
used_dashboards = {}


def load_template(fname):
    with open(config["base_dir"] + "templates/" + fname, 'r') as myfile:
        data = myfile.read()
    return data

def apply_parameters(objstr, parameters):
    for _keyName in parameters.keys():
        _target = '<<' + _keyName.upper() + '>>'
        _value = parameters.get(_keyName)
        objstr = objstr.replace(_target, _value)

    return objstr

def create_links(service):

     # Template contains multiple links with multiple variables
     # so for new variables, _PARAMS incremented with new vars
    _PARAMS = dict(servicenow_instance=config["servicenow_instance"],
                   dashboard_uid=service.dashboard_uid
                   )
    _dashboard_template =  ""
    if sysidOK.match(service.dashboard_uid):
        _dashboard_template =  "single_dash_links_template.json"
    else:
        _dashboard_template =  "single_dash_links_customer.json"

    try:
        _links_text = load_template(_dashboard_template)
        _links_text = apply_parameters(_links_text, _PARAMS)
    except Exception as e:
        logging.error("Dashboard Links creation error: " + e.message)
        print("Dashboard Links creation error: " + e.message)

    return _links_text


def create_panel_links(panel):


    # Template contains multiple links with multiple variables
    # so for new variables, _PARAMS incremented with new vars
    _PARAMS = dict(servicenow_instance = config["servicenow_instance"],
                   graph_panel_sys_id  = panel.graph_panel_sys_id
                   )


    _links_text = ''
    try:
        _links_text = load_template("single_panel_links_template.json")
        _links_text = apply_parameters(_links_text, _PARAMS)
    except Exception as e:
        logging.error("Dashboard Panel Links creation error: " + e.message)
        print("Dashboard Panel Links creation error: " + e.message)

    deep_link=panel.deep_link
    if deep_link != '':
        try:
            _deep_link_text  = load_template("single_panel_deep_link_template.json")
            _DEEP_PARMS      = dict(deep_link=quote(deep_link, safe=':/?&'))
            _deep_link_text  = apply_parameters(_deep_link_text, _DEEP_PARMS)
            if _links_text != '':
                _links_text = _links_text + ", " + _deep_link_text
            else:
                _links_text = _deep_link_text
        except Exception as e:
            logging.error("Dashboard Panel Deep Link creation error: " + e.message)
            print("Dashboard Panel Deep Link creation error: " + e.message)

    return _links_text


def populate_panel(text, service, panel, grid_x, grid_y):
    text = text.replace("<<SERVICE_NAME>>", service.name)
    text = text.replace("<<BASE_METRIC_NAME>>", panel.base_metric_name)
    text = text.replace("<<METRIC_NAME>>", panel.base_metric_name)
    text = text.replace("<<INFLUXDB_METRIC_MEASURE>>", config["influxdb_metric_measure"])
    text = text.replace("<<INFLUXDB_METRIC_POLICY>>", config["influxdb_metric_policy"])
    text = text.replace("<<INFLUXDB_ALERT_MEASURE>>", config["influxdb_alert_measure"])
    text = text.replace("<<INFLUXDB_ALERT_POLICY>>", config["influxdb_alert_policy"])
    text = text.replace("<<PANEL_ID>>", panel.panel_id)
    text = text.replace("<<PANEL_KEY>>", panel.panelKey)
    text = text.replace("<<METRIC_TYPE>>", panel.metric_type)
    text = text.replace("<<TITLE>>", panel.title)
    text = text.replace("<<FORMAT>>", panel.format)
    text = text.replace("<<GRID_X>>", str(grid_x))
    text = text.replace("<<GRID_Y>>", str(grid_y))

    # Generate and add panel links
    panel_links = create_panel_links(panel)
    text = text.replace("<<LINKS>>", panel_links)

    return text


def remove_obsolete_dashboards(org_id_array):
    for org_id in org_id_array:
        all_dashboards = dashboards[org_id].get_dashboards()
        for uid, title in all_dashboards.items():
            try:
                if 'Unhealthy' not in title:
                    if org_id in used_dashboards:
                        if uid not in used_dashboards[org_id]:
                            print("Removing Dash: " + str(uid) + " Title: " + title + " Org: ", str(org_id))
                            dashboards[org_id].delete_dashboard(uid)
                    else:
                        print("Removing Dash: " + str(uid) + " Title: " + title + " Org: ", str(org_id))
                        dashboards[org_id].delete_dashboard(uid)
            except:
                print("Something went wrong trying to delete dashboard with uid: " + str(uid) + " from org: " + str(org_id))


def remove_obsolete_folders(org_id_array):
    for org_id in org_id_array:
        all_folders = folders[org_id].get_folders()
        for uid, title in all_folders.items():
            try:
                if org_id in used_folders:
                    if uid not in used_folders[org_id]:
                        if title != "General":
                            print("Removing Folder: " + str(uid) + " Title: " + title + " Org: ", str(org_id))
                            folders[org_id].delete_folder(uid)
                else:
                    print("Removing Folder: " + str(uid) + " Title: " + title + " Org: ", str(org_id))
                    folders[org_id].delete_folder(uid)
            except:
                print("Something went wrong trying to delete folder with uid: " + str(uid) + " from org: " + str(org_id))


def get_organization_id_by_name(organization):
    headers = {'content-type': 'application/json'}
    resp = requests.get(shputil.get_grafana_base_api_url() + "orgs/name/" + organization, headers=headers)
    if resp.status_code != 200:
        raise IOError("Error getting organization id: " + resp.text)
    fields = json.loads(resp.content)
    return fields['id']


def add_to_used_dashboards(org_id, dash_uid):
    if org_id not in used_dashboards:
        used_dashboards[org_id] = []
    used_dashboards[org_id].append(dash_uid)


def add_to_used_folders(org_id, folder_uid):
    if org_id not in used_folders:
        used_folders[org_id] = []
    used_folders[org_id].append(folder_uid)


def create_single_dashboard(dashboard_json, service_name, org_id, dash_uid, folder_name):
    print("Creating dashboard for " + service_name + " in org " + str(org_id) + " folder=" + folder_name)


    folders_for_organization = folders[org_id]

    folder_id = 0  # default to General folder

    if folder_name != "General":
        try:
            folder_id = folders_for_organization.get_folder_id(folder_name)
        except Exception, e:
            print("Folder not found for " + folder_name)
            folder_id = -1

        if folder_id < 0:
            print("Creating folder: " + folder_name + " for " + service_name + " in org " + str(org_id))
            folder_id = folders_for_organization.create_folder(folder_name)

    add_to_used_dashboards(org_id, dash_uid)
    add_to_used_folders(org_id, folder_id)

    request_data = dashboard_json.replace("<<FOLDER_ID>>", str(folder_id))
    request_data = request_data.replace("<<FOLDER_NAME>>", folder_name)

    # print "service_name=" + service_name + ",  folder_id=" + str(folder_id)

    dashboards_for_organization = dashboards[org_id]

    resp = dashboards_for_organization.create_dashboard(str(dash_uid), json.loads(request_data))

    if resp.status_code != 200:
        logging.error(
            "Error creating dashboard for: " + service_name + ' in folder: ' + folder_name + ' - ' + resp.text)
        print(
            "Error creating dashboard for: " + service_name + ' in folder: ' + folder_name + ' - ' + resp.text)
    else:
        logging.info("Dashboard created successfully: " + dash_uid)
        print("Dashboard created successfully: " + dash_uid)


def sortable_customers(x):
    if x.overall_service_metric == "true":
       return ("A" + ':' +  x.panel_id)   # force to top
    else:
       return (x.customer_name + ':' + x.panel_id)


def create_service_dashboards(service_cfg, main_org, staging_org):
    for service in service_cfg.get_services():
        if service.state == 'undefined':
            logging.debug("Skipping unconfigured service: " + service.name)
            continue

#        if "Sabre Web Services" not in service.name:
#            continue

        all_panels = ''
        comma = ''
        grid_x = 0
        grid_y = 0
        counter = 0
        panel_count = 0

        for panel in sorted(service.panels, key=sortable_customers):
            if panel.display_state == 'Active':
                panel_count += 1
                panel_text = load_template("single_panel_template.json")
                all_panels = all_panels + comma + populate_panel(panel_text, service, panel, grid_x, grid_y)
                comma = ','
                counter += 1
                grid_x = (counter % columns) * 8
                grid_y = (counter / columns) * 20

        dash_uid = service.dashboard_uid
        dash_text = load_template("single_dashboard_template.json")
        dash_text = dash_text.replace("<<SERVICE_NAME>>", service.name)
        dash_text = dash_text.replace("<<DASHBOARD_UID>>", dash_uid)
        dash_text = dash_text.replace("<<PANELS>>", all_panels)

        # Generate and add dashboard links
        all_links = create_links(service)
        dash_text = dash_text.replace("<<LINKS>>", all_links)


        if service.is_validated():
            org_id = main_org
        else:
            org_id = staging_org

        folder_name = service.report_grouping

        if panel_count > 0:
            try:
                create_single_dashboard(dash_text, service.name, org_id, dash_uid, folder_name)
            except Exception:
                # log it and move on to next dashboard
                logging.error("Dashboard creation error: " + service.name, exc_info=True)
        else:
            logging.info("No panels for service: " + service.name)


def add_single_alert(ci_where, level, ref_id):
    target = load_template("single_alert_template.json")
    target = target.replace("<<CIWHERE>>", ci_where)
    target = target.replace("<<ALERTLEVEL>>", level)
    return target.replace("<<ALERTLETTER>>", ref_id)


def add_single_target(ci_where, alias, ref_id):
    target = load_template("single_target_template.json")
    target = target.replace("<<CIWHERE>>", ci_where)
    target = target.replace("<<refId>>", ref_id)
    return target.replace("<<ALIAS>>", alias)


def create_aggregated_dashboards(service_cfg, agg_org_id):
    for topLevelService in service_cfg.get_topLevelServices():

        all_targets = ''

        # First build all of the individual targets, then build the aggregated one
        # Starting the counter (converts to letter) at 68 (D) to save A-C for total and alerts
        target_counter = 68
        total_count_letter = "A"
        crit_alert_letter = "B"
        warn_alert_letter = "C"
        comma = ''
        delim = ''
        all_ci_where = "(\\\"ci\\\" = "

        ci_where = "(\\\"ci\\\" = '" + topLevelService.name + "')"
        all_ci_where = all_ci_where + delim + "'" + topLevelService.name + "'"
        delim = ' OR \\\"ci\\\" = '
        all_targets = all_targets + comma + add_single_target(ci_where, topLevelService.name + " Transaction Count",
                                                              chr(target_counter))
        comma = ','

        if len(topLevelService.children) > 0:
            for child in topLevelService.children:
                # Need to stick to the alphabet
                if target_counter == 90:
                    target_counter = 96
                if target_counter == 122:
                    target_counter = 69
                target_counter += 1

                ci_where = "(\\\"ci\\\" = '" + child.name + "')"
                all_ci_where = all_ci_where + delim + "'" + child.name + "'"
                # Found with SynXis that too many children are a problem, since Grafana groups all target
                # queries into one call, and that ends up too long.
                # If there are 7 or fewer children, include them all
                # If there are more than 7, include only the first few
                if target_counter <= 70 or len(topLevelService.children) < 8:
                    delim = ' OR \\\"ci\\\" = '
                    all_targets = all_targets + comma + add_single_target(ci_where, child.name + " Transaction Count",
                                                                          chr(target_counter))
                comma = ','
        all_ci_where = all_ci_where + ')'

        all_targets = all_targets + comma + add_single_target(all_ci_where, "Combined Transaction Count",
                                                              total_count_letter)
        comma = ','

        all_targets = all_targets + comma + add_single_alert(all_ci_where, "CRITICAL", crit_alert_letter)
        all_targets = all_targets + comma + add_single_alert(all_ci_where, "WARNING", warn_alert_letter)

        panel_text = load_template("total_single_panel_template.json")
        panel_text = panel_text.replace("<<CRITALERTLETTER>>", crit_alert_letter)
        panel_text = panel_text.replace("<<WARNALERTLETTER>>", warn_alert_letter)
        panel_text = panel_text.replace("<<TARGETS>>", all_targets)

        dash_uid = topLevelService.dashboard_uid
        dash_text = load_template("single_dashboard_template.json")
        dash_text = dash_text.replace("<<SERVICE_NAME>>", "Aggregate " + topLevelService.name)
        dash_text = dash_text.replace("<<DASHBOARD_UID>>", dash_uid)
        dash_text = dash_text.replace("<<PANELS>>", panel_text)

        dash_text = dash_text.replace("<<LINKS>>", "")  # No links for aggregated dashboards

        folder_name = topLevelService.report_grouping

        try:
            # print(dash_text)
            create_single_dashboard(dash_text, topLevelService.name, agg_org_id, dash_uid, folder_name)
        except Exception:
            # log it and move on to next dashboard
            logging.error("Dashboard creation error: " + topLevelService.name, exc_info=True)


def load_folders(org_id_array):
    for org_id in org_id_array:
        folders[org_id] = Folders(org_id)


def load_dashboards(org_id_array):
    for org_id in org_id_array:
        dashboards[org_id] = Dashboards(org_id)


#===== Version of create_service_dashboards but for customers
def create_customer_dashboards(customers_cfg, main_org, staging_org):

    customers_list = customers_cfg.get_customers()
    for customer in customers_list:
        if customer.state == 'undefined':
            logging.debug("Skipping unconfigured customer: " + customer.name)
            continue

        all_panels = ''
        comma = ''
        grid_x = 0
        grid_y = 0
        counter = 0
        panel_count = 0

        for panel in customer.panels:
            if panel.display_state == 'Active':
                panel_count += 1
                panel_text = load_template("single_panel_template.json")
                all_panels = all_panels + comma + populate_panel(panel_text, customer, panel, grid_x, grid_y)
                comma = ','
                counter += 1
                grid_x = (counter % columns) * 8
                grid_y = (counter / columns) * 20

        dash_uid   = customer.dashboard_uid
        dash_title = customer.customer_name + " (" + customer.customer_code + ")"

        dash_text = load_template("single_dashboard_template.json")
        dash_text = dash_text.replace("<<SERVICE_NAME>>", dash_title)
        dash_text = dash_text.replace("<<DASHBOARD_UID>>", dash_uid)
        dash_text = dash_text.replace("<<PANELS>>", all_panels)

        # Generate and add dashboard links
        all_links = create_links(customer)
        dash_text = dash_text.replace("<<LINKS>>", all_links)


        if customer.is_validated():
            org_id = main_org
        else:
            org_id = staging_org

        folder_name = customer.report_grouping

        if panel_count > 0:
            try:
                create_single_dashboard(dash_text, customer.customer_name, org_id, dash_uid, folder_name)
            except Exception:
                # log it and move on to next dashboard
                logging.error("Dashboard creation error: " + customer.customer_name, exc_info=True)
        else:
            logging.info("No panels for Customer: " + customer.customer_name)



#============= MAIN =========================================================
config = shputil.get_config()
shputil.configure_logging(config["logging_configuration_file"])

main_org_id = 1
staging_org_id = 2
aggregate_org_id = 3

try:
    service_config = ServiceConfiguration()

    main_org_id = get_organization_id_by_name('Main%20Org%2E')
    staging_org_id = get_organization_id_by_name('Staging')
    aggregate_org_id = get_organization_id_by_name('Aggregate')

    load_dashboards([main_org_id, staging_org_id, aggregate_org_id])
    load_folders([main_org_id, staging_org_id, aggregate_org_id])

    create_service_dashboards(service_config, main_org_id, staging_org_id)
    create_aggregated_dashboards(service_config, aggregate_org_id)

    # Code for customers dashboard to turn on by uncommenting the following 2 lines
    customer_config = CustomerConfiguration(service_config)
    create_customer_dashboards(customer_config,main_org_id, staging_org_id)

    remove_obsolete_dashboards([main_org_id, staging_org_id, aggregate_org_id])
    remove_obsolete_folders([main_org_id, staging_org_id, aggregate_org_id])

except Exception, e:
    print(str(e))
    logging.error("Failure: Fatal error when creating dashboards", exc_info=True)

sys.exit(0)
