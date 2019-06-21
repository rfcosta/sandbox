from threshold import Threshold

class Panel():
    def __init__(self, panel, panelKey, use_configured_panelIDs, service_name):
        self.use_configured_panelIDs = use_configured_panelIDs
        self.thresholds = []
        self.service_name = service_name
        self.display_state = panel['display_state']
        self.deep_link = panel['deep_link']
        self.title = panel['title']
        self.base_metric_name = panel['base_metric_name']
        self.format = panel['format']
        self.alerting_enabled = panel['alerting_enabled'] if 'alerting_enabled' in panel else 'false'
        self.dynamic_alerting_enabled = panel['dynamic_alerting_enabled'] if 'dynamic_alerting_enabled' in panel else 'false'
        self.static_alerting_enabled_high = panel[
            'static_alerting_enabled_high'] if 'static_alerting_enabled_high' in panel else self.alerting_enabled
        self.static_alerting_enabled_low = panel[
            'static_alerting_enabled_low'] if 'static_alerting_enabled_low' in panel else self.alerting_enabled
        self.dynamic_alerting_enabled_high = panel[
            'dynamic_alerting_enabled_high'] if 'dynamic_alerting_enabled_high' in panel else self.dynamic_alerting_enabled
        self.dynamic_alerting_enabled_low = panel[
            'dynamic_alerting_enabled_low'] if 'dynamic_alerting_enabled_low' in panel else self.dynamic_alerting_enabled
        self.overall_service_metric = panel['overall_service_metric'] if 'overall_service_metric' in panel else 'false'
        self.threshold_violation_window = panel[
            'threshold_violation_window'] if 'threshold_violation_window' in panel else 2
        self.threshold_violation_occurrences = panel[
            'threshold_violation_occurrences'] if 'threshold_violation_occurrences' in panel else 2
        self.static_threshold_violation_window = panel[
            'static_threshold_violation_window'] if 'static_threshold_violation_window' in panel else self.threshold_violation_window
        self.static_threshold_violation_occurrences = panel[
            'static_threshold_violation_occurrences'] if 'static_threshold_violation_occurrences' in panel else self.threshold_violation_occurrences
        self.dynamic_threshold_violation_window = panel[
            'dynamic_threshold_violation_window'] if 'dynamic_threshold_violation_window' in panel else self.threshold_violation_window
        self.dynamic_threshold_violation_occurrences = panel[
            'dynamic_threshold_violation_occurrences'] if 'dynamic_threshold_violation_occurrences' in panel else self.threshold_violation_occurrences
        self.metric_type = panel['metric_type']
        self.panelKey = panelKey
        self.kpi = panel['kpi']
        self.panel_id = self.get_panel_id(panel)
        self.load_thresholds(panel)
        self.graph_panel_sys_id = panel["graph_panel_sys_id"] if "graph_panel_sys_id" in panel else ''
        self.customer_code = panel['customer_code']
        self.customer_name = panel['customer_name']
        self.customer_sys_id = panel['customer_sys_id']

    def get_panel_id(self, panel):
        if self.use_configured_panelIDs == 'true':
            return panel['panel_id']
        else:
            return self.get_old_panel_id_for_metric()

    # temporary until we figure out the SNOW/SHP mismatched versions problem

    def get_old_panel_id_for_metric(self):
        if self.metric_type == 'avg_processing_time':
            return '3'
        if self.metric_type == 'transaction_count':
            return '4'
        if self.metric_type == 'error_count':
            return '5'
        if self.metric_type == 'error_rate':
            return '6'
        print "Unable to determine panel id for metric type"

    def load_thresholds(self, panel):
        thresholds = panel['thresholds']
        my_threshold = Threshold(thresholds)
        self.thresholds = my_threshold

    def __str__(self):
        s = ("    panel: " + '\n' +
             "      display_state:                  " + self.display_state + '\n' +
             "      panel_id:                       " + self.panel_id + '\n' +
             "      graph_panel_sys_id:             " + self.graph_panel_sys_id + '\n' +
             "      overall_service_metric:         " + self.overall_service_metric + '\n' +
             "      deep_link:                      " + self.deep_link + '\n' +
             "      title:                          " + self.title + '\n' +
             "      base_metric_name:               " + self.base_metric_name + '\n' +
             "      format:                         " + self.format + '\n' +
             "      Old alerting_enabled:           " + self.alerting_enabled + '\n' +
             "      Old dynamic_alerting_enabled:   " + self.dynamic_alerting_enabled + '\n' +
             "      static_alerting_enabled_high:   " + self.static_alerting_enabled_high + '\n' +
             "      static_alerting_enabled_low:    " + self.static_alerting_enabled_low + '\n' +
             "      dynamic_alerting_enabled_high:  " + self.dynamic_alerting_enabled_high + '\n' +
             "      dynamic_alerting_enabled_low:   " + self.dynamic_alerting_enabled_low + '\n' +
             "      Old alert_window:               " + str(self.threshold_violation_window) + '\n' +
             "      Old alert_tolerance:            " + str(self.threshold_violation_occurrences) + '\n' +
             "      static_alert_window:            " + str(self.static_threshold_violation_window) + '\n' +
             "      static_alert_tolerance:         " + str(self.static_threshold_violation_occurrences) + '\n' +
             "      dynamic_alert_window:           " + str(self.dynamic_threshold_violation_window) + '\n' +
             "      dynamic_alert_tolerance:        " + str(self.dynamic_threshold_violation_occurrences) + '\n' +
             "      metric_type:                    " + self.metric_type + '\n' +
             "      panelKey:                       " + self.panelKey + '\n' +
             "      service_name:                   " + self.service_name + '\n' +
             "      customer_name:                  " + self.customer_name + '\n' +
             "      customer_code:                  " + self.customer_code + '\n' +
             "      customer_sys_id:                " + self.customer_sys_id + '\n' +
             "      kpi:                            " + self.kpi + '\n')
        s = s + self.thresholds.to_string()
        return s
