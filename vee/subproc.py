import datetime
import functools
import logging
import os
import subprocess
import sys
import threading
import errno

from vee import log
from vee.cli import style
from vee.envvars import join_env_path


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
                self.callbacks.append(self.log_chunk)
                self.verbosity = max(3, self.verbosity or 0) # Bump it into super verbose territory.
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
            logger = self.logger = logging.getLogger('vee.subproc.[%d].%s' % (self.proc.pid, self.name))
        if self.return_buffer:
            logger.debug(chunk, extra={'verbosity': self.verbosity, 'from_subproc': True})
        else:
            logger.info(chunk, extra={'verbosity': self.verbosity, 'from_subproc': True})

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
            try:
                # Need to use os.read instead of fh.read so that there is no
                # buffering at all.
                chunk = os.read(fd, size)
            except OSError as e:
                # We get tons of these on linux. Not really sure why...
                if e.errno == errno.EIO:
                    break
                raise
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
        _frame=kwargs.pop('_frame', 0) + 3
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

    if kwargs.pop('vee_in_env', False):
        env = kwargs.get('env', os.environ).copy()
        env['PYTHONPATH'] = join_env_path(os.path.join(VEE, 'src'), env.get('PYTHONPATH'))
        env['PATH'] = join_env_path(os.path.join(VEE, 'bin'), env.get('PATH'))
        kwargs['env'] = env

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


def bash_source(shell_script, callbacks=None, prologue='', epilogue='', **kwargs):

    if not callbacks:
        return call(['bash', '-c', '%s\nsource %s\n%s' % (prologue, shell_script, epilogue)], **kwargs)

    prfd, cwfd = os.pipe()
    crfd, pwfd = os.pipe()

    try:

        def callback_target():
            
            try:
                fh = os.fdopen(prfd)
            except:
                os.close(prfd)
                raise

            while True:
                arg_count = fh.readline().strip()
                if not arg_count:
                    break
                arg_count = int(arg_count)
                args = []
                for arg_i in xrange(arg_count):
                    arg_len = int(fh.readline())
                    args.append(fh.read(arg_len))
                name = args[0]
                if name in callbacks:
                    try:
                        res = callbacks[name](*args[1:])
                    except Exception as e:
                        log.exception('exception in callback %s: %s' % (name, e))
                        res = None
                else:
                    log.warning('no callback %s' % name)
                    res = None
                if res is None:
                    os.write(pwfd, '0\n')
                else:
                    res = str(res)
                    os.write(pwfd, '%s\n' % len(res))
                    os.write(pwfd, res)

        thread = threading.Thread(target=callback_target)
        thread.daemon = True
        thread.start()

        funcs = '\n'.join('%s() { _vee_callback %s "$@"; }' % (name, name) for name in callbacks)
        cmd = ['bash', '-c', '''
            _vee_callback() {

                local rfd=%d;
                local wfd=%d;

                # Write args to Python.
                echo ${#@} >&$wfd
                for x in "$@"; do
                    echo ${#x} >&$wfd
                    echo -n "$x" >&$wfd
                done

                # Read res from Python.
                local len
                read -u $rfd len
                if [[ $len != 0 ]]; then
                    local res
                    read -u $rfd -n $len res
                    echo "$res"
                fi

            }
            %s
            %s
            source %s
            %s
        ''' % (crfd, cwfd, funcs, prologue, shell_script, epilogue)]

        res = call(cmd, **kwargs)

        os.close(cwfd); cwfd = None
        os.close(crfd); crfd = None

        thread.join()

        return res

    finally:
        if cwfd: os.close(cwfd)
        if crfd: os.close(crfd)
        if pwfd: os.close(pwfd)
        # Don't need to close the prfd since it will be done so implicitly by
        # the thread.



def which(name):
    bases = os.environ['PATH'].split(':')
    for base in bases:
        path = os.path.join(os.path.expanduser(base), name)
        if os.path.exists(path):
            return path

