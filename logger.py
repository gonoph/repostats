# taken from http://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
# author: http://stackoverflow.com/users/48087/airmind
# author: http://stackoverflow.com/users/404321/guillaume-algis

import logging
import repostats

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

#The background is set with 40 plus the number of the color, and the foreground with 30

#These are the sequences need to get colored ouput
RESET_SEQ = '\033[0m'
UNBOLD_SEQ = '\033[22m'
COLOR_SEQ = '\033[0;%dm'
BOLD_SEQ = '\033[1m'

def ansi(message, use_color = True):
    if use_color:
        message = message.replace('$RESET', RESET_SEQ).replace('$BOLD', BOLD_SEQ).replace('$UNBOLD', UNBOLD_SEQ)
    else:
        message = message.replace('$RESET', '').replace('$BOLD', '').replace('$UNBOLD', '')
    return message

COLORS = {
    'WARNING': YELLOW,
    'INFO': CYAN,
    'DEBUG': BLUE,
    'CRITICAL': YELLOW,
    'ERROR': RED
}

class ColoredFormatter(logging.Formatter):
    def __init__(self, msg, use_color = True):
        logging.Formatter.__init__(self, msg)
        self.use_color = use_color

    def format(self, record):
        levelname = record.levelname
        if self.use_color and levelname in COLORS:
	    levelname_color = COLOR_SEQ % (30 + COLORS[levelname]) + levelname + UNBOLD_SEQ
	    record.levelname = levelname_color
        return logging.Formatter.format(self, record)

class ColoredLogger(logging.Logger):
    FORMAT = '%(levelname)-20s [$BOLD%(name)-30.30s$UNBOLD]  %(message)s$RESET'
    _format = FORMAT
    @staticmethod
    def setFormat(f):
	ColoredLogger._format = f
    def __init__(self, name, level=logging.NOTSET):
	super(ColoredLogger, self).__init__(name, level)
	color_formatter = ColoredFormatter(ansi(ColoredLogger._format, True))
	console = logging.StreamHandler()
	console.setFormatter(color_formatter)
	console.setLevel(5)
	self.addHandler(console)

def setRootLogger():
    global repostats
    root = ColoredLogger('root')
    root.setLevel(logging.WARN)
    logging.root = root
    logging.Logger.root = root
    logging.Logger.manager = logging.Manager(root)
    repostats.log = logging.getLogger(repostats.log.name)

# logging.setLoggerClass(ColoredLogger)

# vim: sw=4 cindent
