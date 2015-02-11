import errno
import os
import subprocess


def _print_call(cmd):
    print colour('$', 'blue', bright=True), colour(cmd[0], 'black', bright=True), colour(' '.join(cmd[1:]), reset=True)


def call(cmd, **kw):
    if not kw.pop('silent', False):
        _print_call(cmd)
    subprocess.check_call(cmd, **kw)


def call_output(cmd, **kw):
    if not kw.pop('silent', False):
        _print_call(cmd)
    return subprocess.check_output(cmd, **kw)


def makedirs(*args):
    path = os.path.join(*args)
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e
    return path


CSI = '\x1b['
_colours = dict(
    black=0,
    red=1,
    green=2,
    yellow=3,
    blue=4,
    magenta=5,
    cyan=7,
    white=7,
)


def colour(message, fg=None, bg=None, bright=False, reset=False):
    parts = []
    if fg is not None:
        parts.extend((CSI, '3', str(_colours[fg]), 'm'))
    if bg is not None:
        parts.extend((CSI, '4', str(_colours[bg]), 'm'))
    if bright:
        parts.extend((CSI, '1m'))
    parts.append(message)
    if reset:
        parts.extend((CSI, '0m'))
    return ''.join(parts)

