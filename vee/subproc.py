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

    def __init__(self, specs, name, verbosity=0, pty=None):

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

        if pty is None:
            pty = not self.return_buffer

        if pty:
            try:
                self.master_fd, self.slave_fd = os.openpty()
            except OSError:
                self.master_fd, self.slave_fd = os.pipe()
        else:
            self.master_fd, self.slave_fd = os.pipe()

    def __del__(self):
        self.close()

    def close(self):
        if self.master_fd is not None:
            os.close(self.master_fd)
            self.master_fd = None
        if self.slave_fd is not None:
            os.close(self.slave_fd)
            self.slave_fd = None

    def log_chunk(self, chunk):
        logger = self.logger
        if logger is None:
            logger = self.logger = logging.getLogger('vee.subproc[%d].%s' % (self.proc.pid, self.name))
        logger.info(chunk, extra={'verbosity': self.verbosity})

    def start(self, proc):

        os.close(self.slave_fd)
        self.slave_fd = None

        self.proc = proc
        self.thread = threading.Thread(target=self._target)
        self.thread.daemon = True
        self.thread.start()

    def _target(self):
        fd = self.master_fd
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
        self.close()


def call(cmd, **kwargs):

    # Log the call.
    kwargs.pop('silent', None) # B/C.
    VEE = os.environ.get('VEE')
    cmd_collapsed = [x.replace(VEE, '$VEE') if VEE else x for x in cmd]
    log.debug(
        '$ ' + ' '.join(cmd_collapsed),
        verbosity=2,
        _frame=3,
    )

    check = kwargs.pop('check', True)
    
    verbosity = kwargs.pop('verbosity', 0)
    indent = kwargs.pop('indent', False)
    if indent:
        indent = log.indent()
        indent.__enter__()

    pty = kwargs.pop('pty', None)
    stdout = _CallOutput(kwargs.pop('stdout', None), 'stdout', verbosity, pty=pty)
    stderr = _CallOutput(kwargs.pop('stderr', None), 'stderr', verbosity, pty=pty)

    proc = subprocess.Popen(cmd, stdout=stdout.slave_fd, stderr=stderr.slave_fd, bufsize=0, **kwargs)
    stdout.start(proc)
    stderr.start(proc)

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


def which(name):
    bases = os.environ['PATH'].split(':')
    for base in bases:
        path = os.path.join(os.path.expanduser(base), name)
        if os.path.exists(path):
            return path

