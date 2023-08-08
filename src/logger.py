import logging
from termcolor import colored


class Logger:

    def __init__(self):
        time_color = 'cyan'
        formatter = self.ColoredFormatter(fmt=colored('%(asctime)s', time_color) + ' - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger = logging.getLogger('app')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(handler)

    def get(self):
        return self.logger

    class ColoredFormatter(logging.Formatter):
        LOG_COLORS = {
            'DEBUG': 'grey',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red',
        }

        def format(self, record):
            levelname = record.levelname
            level_color = self.LOG_COLORS.get(levelname, 'white')
            colored_levelname = colored(levelname, color=level_color)
            record.levelname = colored_levelname

            return super().format(record)
