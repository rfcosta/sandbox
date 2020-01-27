import logging
from logging  import getLogger, DEBUG, INFO, WARNING, ERROR

LOG_LEVEL_DEFAULT = DEBUG
NAME_DEFAULT = __name__

class LoggerUtil(object):
    def __init__(self, NAME=NAME_DEFAULT, LOG_LEVEL=LOG_LEVEL_DEFAULT):
        _logger = getLogger(NAME)

        if _logger.handlers.__len__() == 0:
            _logger.propagate = 0
            _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s %(funcName)s:%(lineno)d: %(message)s')
            _console_handler = logging.StreamHandler()
            _console_handler.setFormatter(_formatter)
            _logger.addHandler(_console_handler)

        self.loggger = _logger
        self.loggger.setLevel(LOG_LEVEL)

        pass
    pass

    def setLevel(self, log_level):
        if log_level in [DEBUG, INFO, WARNING, ERROR]:
            self.loggger.setLevel(log_level)
            pass
        pass




