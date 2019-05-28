class Threshold():

    standard_deviations_mappings = {
        'StandardDeviation+3': 3,
        'StandardDeviation+4': 4,
        'StandardDeviation+5': 5,
    }

    DEFAULT_STANDARD_DEVIATIONS = 4

    def __init__(self, threshold):
        self.warn_lower = float(str(threshold['warn'][0]))
        self.warn_upper = float(str(threshold['warn'][1]))
        self.crit_lower = float(str(threshold['crit'][0]))
        self.crit_upper = float(str(threshold['crit'][1]))
        self.standard_deviations = self.get_standard_deviations(threshold['dynamic'])


    def get_standard_deviations(self, dynamic_threshold_settings):
        if dynamic_threshold_settings in self.standard_deviations_mappings:
            return self.standard_deviations_mappings[dynamic_threshold_settings]
        else:
            return self.DEFAULT_STANDARD_DEVIATIONS


    def to_string(self):
        s = ('       thresholds: ' + '\n' +
             "         warn_lower: " + str(self.warn_lower) + '\n' +
             "         warn_upper: " + str(self.warn_upper) + '\n' +
             "         crit_lower: " + str(self.crit_lower) + '\n' +
             "         crit_upper: " + str(self.crit_upper) + '\n' +
             "         deviations: " + str(self.standard_deviations) + '\n')
        return s
