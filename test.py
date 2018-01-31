import logging
import logging.handlers

log = logging.getLogger(__name__)

log.setLevel(logging.DEBUG)

handler = logging.handlers.SysLogHandler(address=('127.0.0.1', 5140))

formatter = logging.Formatter('%(module)s.%(funcName)s: %(message)s')
handler.setFormatter(formatter)

log.addHandler(handler)


if __name__ == '__main__':
    log.debug('this is a debug message')
    log.critical('this is a critical message')
    log.warning('this is a warning')
