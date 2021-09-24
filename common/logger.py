import logging

DEAFULT_LOG_FMT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
DEAFULT_LOG_PATH = './slackerr.log'


class Logger2(object):
    def __init__(self,
                 log_level=logging.INFO,
                 log_fmt=DEAFULT_LOG_FMT,
                 log_path=DEAFULT_LOG_PATH):

        self.log_level = log_level
        self.log_fmt = log_fmt
        self.log_path = log_path

    def __get_log_formatter(self):
        return logging.Formatter(self.log_fmt)

    def __get_log_f_handler(self, log_formatter):
        f_handler = logging.FileHandler(self.log_path)
        f_handler.setFormatter(log_formatter)
        return f_handler

    def get_logger(self, log_name):
        logger = logging.getLogger(log_name)
        logger.setLevel(self.log_level)

        log_formatter = self.__get_log_formatter()
        f_handler = self.__get_log_f_handler(log_formatter)

        logger.addHandler(f_handler)

        return logger


LOGGER2 = Logger2()


def get_logger(name):
    logger = LOGGER2.get_logger(name)
    return logger