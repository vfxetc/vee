import contextlib
import logging
import sys

from vee.globals import Stack
from vee.cli import style


root = logging.getLogger('vee')
root.setLevel(logging.DEBUG)

# Generally, we don't want our logs to enter the main logging system.
root.propagate = False


_config_stack = Stack()
config = _config_stack.proxy()

config.indent = ''
config.style = {}
config.verbosity = 0


@contextlib.contextmanager
def indent(prefix='  ', postfix=''):
    config = _config_stack.push()
    config.indent = prefix + config.indent + postfix
    try:
        yield
    finally:
        _config_stack.pop()


@contextlib.contextmanager
def capture(name='vee'):
    logger = logging.getLogger(name)
    logs = []
    handler = CallbackHandler(logs.append)
    logger.addHandler(handler)
    try:
        yield logs
    finally:
        logger.removeHandler(handler)

    
class CallbackHandler(logging.Handler):

    def __init__(self, func):
        super(CallbackHandler, self).__init__()
        self.func = func

    def emit(self, record):
        self.format(record)
        self.func(record)



_default_verbosity = {
    logging.DEBUG: 2
}

class StdoutHandler(logging.Handler):
    
    def filter(self, record):
        # Make sure it isn't too verbose. DEBUG messages default to level 2,
        # and everything else gets through. If we introduct TRACE or BLATHER
        # levels, we may drop DEBUG to verbosity 1.
        verbosity = getattr(record, 'verbosity', None)
        if verbosity is None:
            verbosity = _default_verbosity.get(record.levelno, 0)
        return verbosity <= config.verbosity

    def format(self, record):
        record.message = record.msg % record.args if record.args else record.msg
        if record.levelname == 'DEBUG':
            record.message = style('Debug [%s:%s]: %s' % (record.name, record.lineno or '', record.message), faint=True)
        elif record.levelname != 'INFO':
            colour = {'WARNING': 'yellow'}.get(record.levelname, 'red')
            record.message = '%s %s' % (
                style(record.levelname.title() + ':', fg=colour),
                record.message,
            )
        return record.message

    def emit(self, record):
        indent = config.indent
        msg = self.format(record)
        for line in msg.splitlines():
            print indent + line


root.addHandler(StdoutHandler())



def log(level, message, verbosity=None, name=None, _frame=1):

    # We must manually construct a LogRecord, and "handle" it, since we want
    # to set the lineno to be further up the pipe.
    
    frame = sys._getframe(_frame)
    code = frame.f_code
    name = name or frame.f_globals['__name__']

    logger = logging.getLogger(name)
    record = logger.makeRecord(name, level, code.co_filename, frame.f_lineno, message, (), None, code.co_name, {'verbosity': verbosity})
    logger.handle(record)


def debug(*args, **kwargs):
    kwargs.setdefault('_frame', 2)
    log(logging.DEBUG, *args, **kwargs)
def info(*args, **kwargs):
    kwargs.setdefault('_frame', 2)
    log(logging.INFO, *args, **kwargs)
def warning(*args, **kwargs):
    kwargs.setdefault('_frame', 2)
    log(logging.WARNING, *args, **kwargs)
def error(*args, **kwargs):
    kwargs.setdefault('_frame', 2)
    log(logging.ERROR, *args, **kwargs)
def critical(*args, **kwargs):
    kwargs.setdefault('_frame', 2)
    log(logging.CRITICAL, *args, **kwargs)


if __name__ == '__main__':

    info('PUTS', name='vee.puts', verbosity=2)


    main = logging.getLogger('vee.log.main')
    main.info('info message', extra={'verbosity': 0})
    main.warning('warning message', extra={'verbosity': 0})
    
    with capture() as logs, indent():
        main.debug('Indented debug')
        main.info('Indented info')
        main.warning('Indented warning')
        main.error('Indenter error')

    print 'Captured', len(logs), 'logs:'
    for rec in logs:
        print rec.message


