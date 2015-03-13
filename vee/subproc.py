import datetime
import functools
import os
import subprocess
import sys
import threading

from vee.cli import style


def _call_reader(fh, size=2**10, buffer=None, callback=None, stream=None):
    while True:
        chunk = fh.read(size)
        if not chunk:
            return
        if buffer is not None:
            buffer.append(chunk)
        if callback is not None:
            callback(chunk)
        if stream is not None:
            stream.write(chunk)


def call(cmd, **kwargs):

    # Print out the call to the console.
    # TODO: vary this depending on global verbosity.
    if not kwargs.pop('silent', True):
        VEE = os.environ.get('VEE')
        cmd_collapsed = [x.replace(VEE, '$VEE') if VEE else x for x in cmd]
        print style('$', 'blue', bold=True), style(cmd_collapsed[0], bold=True), ' '.join(cmd_collapsed[1:])

    check = kwargs.pop('check', True)

    stdout = kwargs.pop('stdout', None)
    on_stdout = kwargs.pop('on_stdout', None)
    stderr = kwargs.pop('stderr', None)
    on_stderr = kwargs.pop('on_stderr', None)

    if stdout or on_stdout:
        kwargs['stdout'] = subprocess.PIPE
        kwargs['bufsize'] = 0
    if stderr or on_stderr:
        kwargs['stderr'] = subprocess.PIPE
        kwargs['bufsize'] = 0

    proc = subprocess.Popen(cmd, **kwargs)
    threads = []

    if stdout or on_stdout:
        stdout_buffer = []
        stdout_thread = threading.Thread(target=_call_reader, kwargs=dict(
            fh=proc.stdout,
            callback=on_stdout,
            buffer=stdout_buffer if stdout else None,
        ))
        stdout_thread.daemon = True
        stdout_thread.start()
        threads.append(stdout_thread)

    if stderr or on_stderr:
        stderr_buffer = []
        stderr_thread = threading.Thread(target=_call_reader, kwargs=dict(
            fh=proc.stderr,
            callback=on_stderr,
            buffer=stderr_buffer if stderr else None,
        ))
        stderr_thread.daemon = True
        stderr_thread.start()
        threads.append(stderr_thread)

    proc.wait()
    for thread in threads:
        thread.join()

    if (check or stdout or stderr) and proc.returncode:
        raise subprocess.CalledProcessError(proc.returncode, cmd)

    if stdout and stderr:
        return ''.join(stdout_buffer), ''.join(stderr_buffer)
    if stdout:
        return ''.join(stdout_buffer)
    if stderr:
        return ''.join(stderr_buffer)

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

