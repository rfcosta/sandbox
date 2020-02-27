#!/bin/env python3

import json
import sys
import copy
import re

import requests

try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote  # Python3

sys.path.append('/opt/aed/shp/lib')
sys.path.append('/opt/aed/shp/lib/grafana')

import shputil
from service_configuration import ServiceConfiguration
from customer_configuration import CustomerConfiguration
from folders import Folders
from dashboards import Dashboards

sysidOK = re.compile('^[0-9A-Fa-f]{32,32}$')

columns = 3

folders = {}
dashboards = {}

used_folders = {}
used_dashboards = {}

unique_sources = []
unique_types = []
type_labels = {}

dashboards_to_preserve = ("InfluxDB", "Alerts", "Grafana", "Transaction Counts by Source", "Main")


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
    _dashboard_template = ""
    if sysidOK.match(service.dashboard_uid):
        _dashboard_template = "single_dash_links_template.json"
    else:
        _dashboard_template = "single_dash_links_customer.json"

    try:
        _links_text = load_template(_dashboard_template)
        _links_text = apply_parameters(_links_text, _PARAMS)
    except Exception as e:
        logger.exception("Dashboard Links creation error")

    return _links_text


def create_panel_links(panel):
    # Template contains multiple links with multiple variables
    # so for new variables, _PARAMS incremented with new vars
    _PARAMS = dict(servicenow_instance=config["servicenow_instance"],
                   graph_panel_sys_id=panel.graph_panel_sys_id
                   )

    _links_text = ''
    try:
        _links_text = load_template("single_panel_links_template.json")
        _links_text = apply_parameters(_links_text, _PARAMS)
    except Exception as e:
        logger.exception("Dashboard Panel Links creation error")

    deep_link = panel.deep_link
    if deep_link != '':
        try:
            _deep_link_text = load_template("single_panel_deep_link_template.json")
            _DEEP_PARMS = dict(deep_link=quote(deep_link, safe=':/?&=#'))
            _deep_link_text = apply_parameters(_deep_link_text, _DEEP_PARMS)
            if _links_text != '':
                _links_text = _links_text + ", " + _deep_link_text
            else:
                _links_text = _deep_link_text
        except Exception as e:
            logger.exception("Dashboard Panel Deep Link creation error")

    return _links_text


def populate_panel(text, panel, grid_x, grid_y):
    text = text.replace("<<SERVICE_NAME>>", panel.service_name)
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
        if org_id == admin_org_id:
            continue
        all_dashboards = dashboards[org_id].get_dashboards()
        for uid, title in all_dashboards.items():
            try:
                if title not in dashboards_to_preserve:
                    if org_id in used_dashboards:
                        if uid not in used_dashboards[org_id]:
                            logger.info("Removing Dash: {0} Title: {1} Org: {2}".format(uid, title, org_id))
                            dashboards[org_id].delete_dashboard(uid)
                    else:
                        logger.info("Removing Dash: {0} Title: {1} Org: {2}".format(uid, title, org_id))
                        dashboards[org_id].delete_dashboard(uid)
            except Exception as e:
                logger.exception("Something went wrong trying to delete dashboard with uid: {0} from org: {1}".format(uid, org_id))


def remove_obsolete_folders(org_id_array):
    for org_id in org_id_array:
        if org_id == admin_org_id:
            continue
        all_folders = folders[org_id].get_folders()
        for uid, title in all_folders.items():
            try:
                if org_id in used_folders:
                    if uid not in used_folders[org_id]:
                        if title != "General":
                            logger.info("Removing Folder: {0} Title: {1} Org: {2}".format(uid, title, org_id))
                            folders[org_id].delete_folder(uid)
                else:
                    logger.info("Removing Folder: {0} Title: {1} Org: {2}".format(uid, title, org_id))
                    folders[org_id].delete_folder(uid)
            except Exception as e:
                logger.exception("Something went wrong trying to delete folder with uid: {0} from org: {1}".format(uid, org_id))


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
    logger.info("Creating dashboard: {0} in org {1} folder={2}".format(service_name, org_id, folder_name))
    folders_for_organization = folders[org_id]

    folder_id = 0  # default to General folder
    if folder_name != "General":
        try:
            folder_id = folders_for_organization.get_folder_id(folder_name)
        except Exception as e:
            logger.exception("Folder not found for {0}".format(folder_name))
            folder_id = -1
        if ((folder_id is None) or (folder_id < 0)):
            logger.error("Creating folder: {0} for {1} in org {2}".format(folder_name, service_name, org_id))
            folder_id = folders_for_organization.create_folder(folder_name)

    add_to_used_dashboards(org_id, dash_uid)
    add_to_used_folders(org_id, folder_id)

    request_data = dashboard_json.replace("<<FOLDER_ID>>", str(folder_id))
    request_data = request_data.replace("<<FOLDER_NAME>>", folder_name)

    # logger.debug("service_name={0}, folder_id={1}".format(service_name, folder_id))

    dashboards_for_organization = dashboards[org_id]
    resp = dashboards_for_organization.create_dashboard(str(dash_uid), json.loads(request_data))

    if resp.status_code != 200:
        msg = "Error creating dashboard: {0} in folder: {1} - {2}".format(service_name, folder_name, resp.text)
        logger.error(msg)
    else:
        msg = "Dashboard created successfully: {0}".format(dash_uid)
        logger.info(msg)


def sortable_customers(x):
    if x.overall_service_metric == "true":
        return "A" + ':' + x.panel_id  # force to top
    else:
        return x.customer_name + ':' + x.panel_id


def create_service_dashboards(service_cfg, main_org, staging_org):
    # Need to fill lists of unique sources and types
    global unique_sources
    global unique_types
    global type_labels

    for service in service_cfg.get_services():
        if service.state == 'undefined':
            logger.debug("Skipping unconfigured service: {0}".format(service.name))
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
                # Add source and type to global lists, for later use
                if panel.metric_type not in unique_types:
                    unique_types.append(panel.metric_type)
                type_labels[panel.metric_type] = panel.base_metric_name
                if panel.data_source not in unique_sources:
                    unique_sources.append(panel.data_source)

                panel_count += 1
                panel_text = load_template("single_panel_template.json")

                # If there is a customer, append panel title with it
                if panel.customer_code == 'ALL':
                    all_panels = all_panels + comma + populate_panel(panel_text, panel, grid_x, grid_y)
                else:
                    panel_copy = copy.copy(panel)
                    customer_code = 'unknown'
                    if panel.customer_code:
                        customer_code = panel.customer_code
                    panel_copy.title = panel.title + " - " + panel.customer_name + " (" + customer_code + ")"
                    all_panels = all_panels + comma + populate_panel(panel_text, panel_copy, grid_x, grid_y)

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
                logger.exception("Dashboard creation error: {0}".format(service.name))
        else:
            logger.info("No panels for service: {0}".format(service.name))


# Creates dashboards with panels from many services, so they can be used to quickly assess
# the overall health of SHP.
def create_shp_health_dashboards(service_cfg, org_id):
    global unique_sources
    global unique_types
    global type_labels

    for metric_type in unique_types:
        folder_name = "Main SHP Health - Type Groups"
        type_label = type_labels[metric_type]

        all_panels = ''
        panel_count = 0
        id_list = []
        comma = ''
        grid_x = 0
        grid_y = 0
        counter = 0

        for service in service_cfg.get_services():
            if service.state != 'validated':
                logger.debug("Skipping non-Validated service: {0}".format(service.name))
                continue

            for panel in sorted(service.panels, key=sortable_customers):
                # We only want those with 'overall_service_metric' = true so we don't have too many panels.
                if panel.display_state == 'Active' and panel.base_metric_name == type_label and panel.overall_service_metric == "true":
                    panel_count += 1
                    panel_text = load_template("single_panel_template.json")
                    # Make a copy of the panel to use, in case we need to change something
                    panel_copy = copy.copy(panel)
                    # Make sure panel_id is unique (for this dashboard)
                    while panel_copy.panel_id in id_list:
                        panel_copy.panel_id = str(int(panel_copy.panel_id) + 1)
                    id_list.append(panel_copy.panel_id)
                    # Add service name to title
                    panel_copy.title = service.name + " - " + panel_copy.title
                    all_panels = all_panels + comma + populate_panel(panel_text, panel_copy, grid_x, grid_y)
                    comma = ','
                    counter += 1
                    grid_x = (counter % columns) * 8
                    grid_y = (counter / columns) * 20

        dash_uid = type_label.replace(" ", "")
        dash_text = load_template("single_dashboard_template.json")
        dash_text = dash_text.replace("<<SERVICE_NAME>>", "ALL " + type_label)
        dash_text = dash_text.replace("<<DASHBOARD_UID>>", dash_uid)
        dash_text = dash_text.replace("<<PANELS>>", all_panels)

        # We don't need links on these graphs
        dash_text = dash_text.replace("<<LINKS>>", "")

        if panel_count > 0:
            try:
                create_single_dashboard(dash_text, "ALL " + type_label, org_id, dash_uid, folder_name)
            except:
                # log it and move on to next dashboard
                logger.exception("Dashboard creation error: All {0}".format(type_label))
        else:
            logger.info("No panels defined?")

    for source in unique_sources:
        folder_name = "Main SHP Health - Source Groups"

        all_panels = ''
        panel_count = 0
        id_list = []
        comma = ''
        grid_x = 0
        grid_y = 0
        counter = 0

        for service in service_cfg.get_services():
            if service.state != 'validated':
                logger.debug("Skipping non-Validated service: {0}".format(service.name))
                continue

            for panel in sorted(service.panels, key=sortable_customers):
                # We only want those with 'overall_service_metric' = true so we don't have too many panels.
                if panel.display_state == 'Active' and panel.data_source == source and panel.overall_service_metric == "true":
                    panel_count += 1
                    panel_text = load_template("single_panel_template.json")
                    # Make a copy of the panel to use, in case we need to change something
                    panel_copy = copy.copy(panel)
                    # Make sure panel_id is unique (for this dashboard)
                    while panel_copy.panel_id in id_list:
                        panel_copy.panel_id = str(int(panel_copy.panel_id) + 1)
                    id_list.append(panel_copy.panel_id)
                    # Add service name to title
                    panel_copy.title = service.name + " - " + panel_copy.title
                    all_panels = all_panels + comma + populate_panel(panel_text, panel_copy, grid_x, grid_y)
                    comma = ','
                    counter += 1
                    grid_x = (counter % columns) * 8
                    grid_y = (counter / columns) * 20

        dash_uid = source.replace(" ", "")
        dash_text = load_template("single_dashboard_template.json")
        dash_text = dash_text.replace("<<SERVICE_NAME>>", "ALL " + source)
        dash_text = dash_text.replace("<<DASHBOARD_UID>>", dash_uid)
        dash_text = dash_text.replace("<<PANELS>>", all_panels)

        # We don't need links on these graphs
        dash_text = dash_text.replace("<<LINKS>>", "")

        if panel_count > 0:
            try:
                create_single_dashboard(dash_text, "ALL " + source, org_id, dash_uid, folder_name)
            except Exception:
                # log it and move on to next dashboard
                logger.exception("Dashboard creation error: ALL {0}".format(source))
        else:
            logger.info("No panels defined?")

    # Now, the dashboard with grouped panels (by ci)


# TODO- this is going to take more.  The 'source' in panel definition is not exactly the same
# TODO - as the 'source' in the database (appdynamics vs. AppDynamics)
# TODO - probably need to query the DB to get list of unique sources with data in last X time
#  influx_measure = str(global_config["influxdb_metric_measure"])
#  influx_db = str(global_config["influxdb_db"])
#  influx_policy = str(global_config["influxdb_metric_policy"])

# query = 'SHOW TAG VALUES ON "kpi" FROM "kpi"."days"."metric\"   WITH key = \"source\"'
#  query = 'SHOW TAG VALUES ON \"' + influx_db + '\" FROM \"' + influx_db + '\".\"' + influx_policy + '\".\"' + influx_measure + \
#          '\" WHERE time > now() - 24h WITH key = \"source\"'

#  logger.debug(query)
#  rs = global_db_connection.query(query)
#  logger.debug(str(rs))

#    all_panels = ''
#    panel_count = 0
#    dashboard_name = "Type by Source"
#    panel_id = 1
#    comma = ''
#    grid_x = 0
#    grid_y = 0
#    counter = 0

#    for source in unique_sources:
#        for type in unique_types:
#            type_label = type_labels[type]

#            panel_count += 1
#            panel_text = load_template("type_by_source_template.json")
#            panel_text = panel_text.replace("<<TITLE>>", source + " - " + type_label)
#            panel_text = panel_text.replace("<<DATA_SOURCE>>", source)
#            panel_text = panel_text.replace("<<METRIC_TYPE>>", type)
#            panel_text = panel_text.replace("<<PANEL_ID>>", str(panel_id))
#            #panel_text = panel_text.replace("<<FORMAT>>", panel.format)
#            panel_text = panel_text.replace("<<GRID_X>>", str(grid_x))
#            panel_text = panel_text.replace("<<GRID_Y>>", str(grid_y))
#            all_panels = all_panels + comma + panel_text
#            comma = ','
#            counter += 1
#            panel_id += 1
#            grid_x = (counter % columns) * 8
#            grid_y = (counter / columns) * 20

#    dash_uid = dashboard_name.replace(" ", "")
#    dash_text = load_template("single_dashboard_template.json")
#    dash_text = dash_text.replace("<<SERVICE_NAME>>", dashboard_name)
#    dash_text = dash_text.replace("<<DASHBOARD_UID>>", dash_uid)
#    dash_text = dash_text.replace("<<PANELS>>", all_panels)

# We don't need links on these graphs
#    dash_text = dash_text.replace("<<LINKS>>", "")

#    folder_name = "Metric Source Aggregates"

#    if panel_count > 0:
#        try:
#            create_single_dashboard(dash_text, dashboard_name, org_id, dash_uid, folder_name)
#        except Exception:
#            # log it and move on to next dashboard
#            logger.error("Dashboard creation error: " + dashboard_name, exc_info=True)
#    else:
#        logger.info("No panels defined?")


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
    for topLevelService in service_cfg.get_top_level_services():

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
            # logger.debug(dash_text)
            create_single_dashboard(dash_text, topLevelService.name, agg_org_id, dash_uid, folder_name)
        except Exception:
            # log it and move on to next dashboard
            logger.exception("Dashboard creation error: {0}".format(topLevelService.name))


def load_folders(org_id_array):
    for org_id in org_id_array:
        folders[org_id] = Folders(org_id)


def load_dashboards(org_id_array):
    for org_id in org_id_array:
        dashboards[org_id] = Dashboards(org_id)


# ===== Version of create_service_dashboards but for customers
def create_customer_dashboards(customers_cfg, main_org, staging_org):
    customers_list = customers_cfg.get_customers()
    for customer in customers_list:
        if customer.state == 'undefined':
            logger.debug("Skipping unconfigured customer: {0}".format(customer.name))
            continue

        all_panels = ''
        comma = ''
        grid_x = 0
        grid_y = 0
        counter = 0
        panel_count = 0
        id_list = []

        for panel in customer.panels:
            if panel.display_state == 'Active':
                panel_count += 1
                panel_text = load_template("single_panel_template.json")
                # Make a copy of the panel to use, in case we need to change something
                panel_copy = copy.copy(panel)
                # Make sure panel_id is unique (for this dashboard)
                while panel_copy.panel_id in id_list:
                    panel_copy.panel_id = str(int(panel_copy.panel_id) + 1)
                id_list.append(panel_copy.panel_id)
                all_panels = all_panels + comma + populate_panel(panel_text, panel_copy, grid_x, grid_y)
                comma = ','
                counter += 1
                grid_x = (counter % columns) * 8
                grid_y = (counter / columns) * 20

        dash_uid = customer.dashboard_uid
        dash_title = customer.name + " (" + customer.code + ")"

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
                create_single_dashboard(dash_text, customer.name, org_id, dash_uid, folder_name)
            except:
                # log it and move on to next dashboard
                logger.error("Dashboard creation error: {0}".format(customer.name))
        else:
            logger.info("No panels for Customer: {0}".format(customer.name))


# ============= MAIN =========================================================

shputil.check_logged_in_user('centos')

config = shputil.get_config()
logger = shputil.get_logger("dashboardCreation")

main_org_id = 1
staging_org_id = 2
aggregate_org_id = 3
admin_org_id = 4

try:
    service_config = ServiceConfiguration()
    global_config = shputil.get_config()

    main_org_id = get_organization_id_by_name('Main%20Org%2E')
    staging_org_id = get_organization_id_by_name('Staging')
    aggregate_org_id = get_organization_id_by_name('Aggregate')
    admin_org_id = get_organization_id_by_name('Admin')

    load_dashboards([main_org_id, staging_org_id, aggregate_org_id, admin_org_id])
    load_folders([main_org_id, staging_org_id, aggregate_org_id, admin_org_id])

    create_service_dashboards(service_config, main_org_id, staging_org_id)
    create_aggregated_dashboards(service_config, aggregate_org_id)
    create_shp_health_dashboards(service_config, admin_org_id)

    # Code for customers dashboard to turn on by uncommenting the following 2 lines
    customer_config = CustomerConfiguration(service_config)
    create_customer_dashboards(customer_config, main_org_id, staging_org_id)

    remove_obsolete_dashboards([main_org_id, staging_org_id, aggregate_org_id, admin_org_id])
    remove_obsolete_folders([main_org_id, staging_org_id, aggregate_org_id, admin_org_id])

except Exception as e:
    logger.exception("Failure: Fatal error when creating dashboards")

sys.exit(0)
