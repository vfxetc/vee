import re
import sys
import traceback

from vee.cli import style, style_error
from vee import log


def cli_exc_str(obj, use_magic=True):
    
    # Need to be able to avoid recursion.
    if use_magic:
        method = getattr(obj, '__cli_str__', None)
        if method:
            return method()

    title = getattr(obj, '__cli_title__', None) or obj.__class__.__name__
    format = getattr(obj, '__cli_format__', None)
    if format is not None:
        message = format.format(self=obj)
    else:
        message = str(obj)
    detail = getattr(obj, '__cli_detail__', None)

    return ('%s %s\n%s' % (
        style('%s:' % title, 'red', bold=True) if title is not None else '',
        style(message,  bold=True) if message is not None else '',
        style(detail, faint=True) if detail is not None else ''
    )).strip()


def cli_errno(e):
    return getattr(e, '__cli_errno__', 1)


def format_cli_exc(e, verbose=False):
    res = ''
    if verbose and sys.exc_traceback:
        stack = traceback.format_list(traceback.extract_tb(sys.exc_traceback))
        res = style(''.join(stack).rstrip(), faint=True) + '\n'
    return res + cli_exc_str(e)

def print_cli_exc(e, verbose=False):
    log.info(format_cli_exc(e, verbose))


def setup_cli_error(e, title=None, format=None, detail=None, errno=1):
    e.__cli_detail__ = detail
    e.__cli_errno__ = errno
    e.__cli_format__ = format
    e.__cli_title__ = title
    return e


class CliMixin(object):

    def __init__(self, *args, **kwargs):
        setup_cli_error(self,
            detail=kwargs.pop('detail', ''),
            errno=kwargs.pop('errno', 1))
        super(CliMixin, self).__init__(*args, **kwargs)


class NotInstalled(RuntimeError):
    __cli_format__ = '{self} is not installed'


class AlreadyInstalled(RuntimeError):
    __cli_format__ = '{self} is already installed'

class AlreadyLinked(RuntimeError):
    __cli_format__ = '{self} is already linked into the environment'

class PipelineError(RuntimeError):
    pass


