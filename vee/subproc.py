import datetime
import functools
import logging
import os
import subprocess
import sys
import threading

from vee.cli import style
from vee import log



class _CallOutput(object):

    def __init__(self, specs, out_stream=None):

        self.callbacks = []
        self.buffer = []
        self.return_buffer = False

        if not isinstance(specs, (list, tuple)):
            specs = [specs]

        for spec in specs:
            if callable(spec):
                self.callbacks.append(spec)
            elif spec is True:
                self.return_buffer = True
                self.callbacks.append(self.buffer.append)
            elif spec is None:
                self.callbacks.append(out_stream.write)
            else:
                raise TypeError('output spec must be True, None, or a callback')

    def start(self, in_stream):
        self.in_stream = in_stream
        self.thread = threading.Thread(target=self._target)
        self.thread.daemon = True
        self.thread.start()

    def _target(self):
        in_stream = self.in_stream
        size = 2**10
        callbacks = self.callbacks
        while True:
            chunk = in_stream.read(size)
            if not chunk:
                return
            for func in callbacks:
                func(chunk)

    def join(self):
        self.thread.join()


def call(cmd, **kwargs):

    # Log the call.
    kwargs.pop('silent', None) # B/C.
    VEE = os.environ.get('VEE')
    cmd_collapsed = [x.replace(VEE, '$VEE') if VEE else x for x in cmd]
    log.debug(
        style('$', 'blue', bold=True) + ' ' + style(cmd_collapsed[0], bold=True) + ' ' + ' '.join(cmd_collapsed[1:]),
        verbosity=2,
        _frame=3,
    )

    check = kwargs.pop('check', True)
    indent = kwargs.pop('indent', True)
    if indent:
        indent = log.indent()
        indent.__enter__()

    stdout = _CallOutput(kwargs.get('stdout'), sys.stdout)
    stderr = _CallOutput(kwargs.get('stderr'), sys.stderr)

    kwargs['stdout'] = kwargs['stderr'] = subprocess.PIPE
    kwargs['bufsize'] = 0

    proc = subprocess.Popen(cmd, **kwargs)
    stdout.start(proc.stdout)
    stderr.start(proc.stderr)

    proc.wait()
    stdout.join()
    stderr.join()

    if indent:
        indent.__exit__(None, None, None)

    if (check or stdout.return_buffer or stderr.return_buffer) and proc.returncode:
        raise subprocess.CalledProcessError(proc.returncode, cmd)

    if stdout.return_buffer and stderr.return_buffer:
        return ''.join(stdout.buffer), ''.join(stderr.buffer)
    if stdout.return_buffer:
        return ''.join(stdout.buffer)
    if stderr.return_buffer:
        return ''.join(stderr.buffer)

    return proc.returncode


def call_output(cmd, **kwargs):
    kwargs['stdout'] = True
    return call(cmd, **kwargs)


def call_log(cmd, **kwargs):

    indent = kwargs.pop('indent', 4)

    buffer_ = []
    def callback(name, echo_fh, echo_format, chunk):
        for line in chunk.splitlines():
            buffer_.append('%s %s %s' % (name, datetime.datetime.utcnow().isoformat('T'), line))
            echo_fh.write(echo_format % line + '\n')

    kwargs.update(
        on_stdout=functools.partial(callback, 'out', sys.stdout, (indent * ' ') + style('%s', faint=True)),
        on_stderr=functools.partial(callback, 'err', sys.stdout, (indent * ' ') + style('%s', 'red')),
    )

    call(cmd, **kwargs)
    return '\n'.join(buffer_)

