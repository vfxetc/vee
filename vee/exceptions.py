import re
from vee.cli import style, style_error


def cli_exc_str(obj, use_magic=True):
    
    # Need to be able to avoid recursion.
    if use_magic:
        method = getattr(obj, '__cli_str__', None)
        if method:
            return method()

    title = getattr(obj, '__cli_title__', None) or re.sub(r'(?<=[^A-Z])([A-Z])', '\1 \2', obj.__class__.__name__)
    message = str(obj)
    detail = getattr(obj, '__cli_detail__', None)
    return '%s %s\n%s' % (
        style('%s: ' % title, 'red', bold=True),
        style(message,  bold=True),
        style(detail, faint=True) if detail is not None else ''
    ).strip()


def cli_errno(e):
    return getattr(e, '__cli_errno__', 1)


class CliException(Exception):

    def __init__(self, *args, **kwargs):
        super(CliException, self).__init__(*args)
        self.errno = kwargs.pop('errno', 1)
        self.__cli_detail__ = kwargs.pop('detail', '')

    def __cli_str__(self):
        return cli_exc_str(self, use_magic=False)


class AlreadyInstalled(CliException, RuntimeError):

    @property
    def __cli_str__(self):
        return style_error(self.args[0] + ' is already installed')


class AlreadyLinked(CliException, RuntimeError):

    @property
    def __cli_str__(self):
        return style_error(self.args[0] + ' is already linked into the environment')

