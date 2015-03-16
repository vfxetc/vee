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

    def __init__(self, specs, name, verbosity=0):

        self.verbosity = verbosity
        self.callbacks = []
        self.buffer = []
        self.return_buffer = False
        self.name = name
        self.logger = None

        if not isinstance(specs, (list, tuple)):
            specs = [specs]

        for spec in specs:
            if callable(spec):
                self.callbacks.append(spec)
            elif spec is True:
                self.return_buffer = True
                self.callbacks.append(self.buffer.append)
            elif spec is None:
                self.callbacks.append(self.log_chunk)
            else:
                raise TypeError('output spec must be True, None, or a callback')

    def log_chunk(self, chunk):
        logger = self.logger
        if logger is None:
            logger = self.logger = logging.getLogger('vee.subproc[%d].%s' % (self.proc.pid, self.name))
        logger.info(chunk, extra={'verbosity': self.verbosity})

    def start(self, proc, in_stream):
        self.proc = proc
        self.in_stream = in_stream
        self.thread = threading.Thread(target=self._target)
        self.thread.daemon = True
        self.thread.start()

    def _target(self):
        fd = self.in_stream.fileno()
        size = 2**10
        callbacks = self.callbacks
        while True:
            # Need to use os.read instead of fh.read so that there is no buffering at all.
            chunk = os.read(fd, size)
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
    
    verbosity = kwargs.pop('verbosity', 0)
    indent = kwargs.pop('indent', False)
    if indent:
        indent = log.indent()
        indent.__enter__()

    stdout = _CallOutput(kwargs.get('stdout'), 'stdout', verbosity)
    stderr = _CallOutput(kwargs.get('stderr'), 'stderr', verbosity)

    kwargs['stdout'] = kwargs['stderr'] = subprocess.PIPE
    kwargs['bufsize'] = 0

    proc = subprocess.Popen(cmd, **kwargs)
    stdout.start(proc, proc.stdout)
    stderr.start(proc, proc.stderr)

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

