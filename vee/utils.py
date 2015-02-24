# encoding: utf8

import datetime
import errno
import functools
import os
import subprocess
import sys
import threading
import time


class cached_property(object):
    
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
    
    def __get__(self, instance, owner_type=None):
        if instance is None:
            return self
        try:
            return instance.__dict__[self.__name__]
        except KeyError:
            value = self.func(instance)
            instance.__dict__[self.__name__] = value
            return value



def makedirs(*args):
    path = os.path.join(*args)
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e
    return path


def _call_reader(fh, size=2**10, buffer=None, callback=None):
    while True:
        chunk = fh.read(size)
        if not chunk:
            return
        if buffer is not None:
            buffer.append(chunk)
        if callback:
            callback(chunk)


def call(cmd, **kwargs):

    if not kwargs.pop('silent', False):
        print colour('$', 'blue', bold=True), colour(cmd[0], bold=True), ' '.join(cmd[1:])

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

    if (stdout or stderr) and proc.returncode:
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



CSI = '\x1b['
_colour_codes = dict(
    black=0,
    red=1,
    green=2,
    yellow=3,
    blue=4,
    magenta=5,
    cyan=6,
    white=7,
)


def _colour_to_code(c):
    if isinstance(c, tuple):
        if len(c) == 3:
            r, g, b = c
            if max(c) <= 5:
                return '8;5;%d' % (16 + 36 * r + 6 * g + b)
            else:
                return '8;2;%d;%d;%d' % (r, g, b)
        if len(c) == 1:
            return '8;5;%d' % (0xe8 + c[0])
    if isinstance(c, basestring):
        return str(_colour_codes[c.lower()])
    if isinstance(c, int):
        return str(c)
    raise ValueError('bad colour %r' % c)





def style(message='', fg=None, bg=None, bright=None, bold=None, faint=None,
          underline=None, blink=None, invert=None, conceal=None,
          prereset=False, reset=True):

    parts = []

    if prereset:
        parts.extend((CSI, '0m'))

    if fg is not None:
        parts.extend((CSI, '9' if bright else '3', _colour_to_code(fg), 'm'))
    if bg is not None:
        parts.extend((CSI, '10' if bright else '4', _colour_to_code(bg), 'm'))

    if bold is not None:
        parts.extend((CSI, '2' if not bold else '', '1m'))
    if faint is not None:
        parts.extend((CSI, '2' if not faint else '', '2m'))
    if underline is not None:
        parts.extend((CSI, '2' if not underline else '', '4m'))
    if blink is not None:
        parts.extend((CSI, '2' if not blink else '', '5m'))
    if invert is not None:
        parts.extend((CSI, '2' if not invert else '', '7m'))
    if conceal is not None:
        parts.extend((CSI, '2' if not conceal else '', '8m'))

    parts.append(message)

    if reset:
        parts.extend((CSI, '0m'))

    return ''.join(parts)


colour = color = style


if __name__ == '__main__':

    print 'ANSI Styles'
    for i in xrange(1, 108):
        print CSI + '0m' + CSI + str(i) + 'm' + ('%03d' % i) + CSI + '0m',
        if i % 10 == 0:
            print
    print
    print

    print 'ANSI Colours'
    swatches = (('Normal', dict()),
                ('Faint',  dict(faint=True)),
                ('Bright', dict(bright=True)),
                ('Bold',   dict(bold=True)),
               )
    for title, _ in swatches:
        print '%-32s' % title,
    print
    for bg in sorted(_colour_codes.values()):
        for _, kwargs in swatches:
            for fg in sorted(_colour_codes.values()):
                print colour(' %d%d' % (fg, bg), fg, bg, **kwargs),
            print colour(reset=True),
        print colour(reset=True)
    print

    print '216 Colours'
    for r in xrange(0, 6):
        for g in xrange(0, 6):
            for b in xrange(0, 6):
                print colour(u'◉ R%dG%dB%d' % (r, g, b), fg=(r, g, b), reset=True),
            print ' '
    print

    print 'Grays'
    for g in xrange(0, 24):
        print colour('%02d' % g, fg=(g, ), reset=True),
    print
    for g in xrange(0, 24):
        print colour('%02d' % g, bg=(g, ), reset=True),
    print
    print

    exit()

    print '24-bit Colours'
    for r in xrange(0, 256, 256/8):
        for g in xrange(0, 256, 256/8):
            for b in xrange(0, 256, 256/8):
                print colour('%02X%02X%02X' % (r, g, b), fg=(r, g, b), reset=True),
            print
    print
