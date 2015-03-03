# encoding: utf8

import datetime
import errno
import fnmatch
import functools
import os
import re
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



def find_in_tree(root, name, type='file'):
    pattern = fnmatch.translate(name)
    for dir_path, dir_names, file_names in os.walk(root):
        # Look for the file/directory.
        candidates = dict(file=file_names, dir=dir_names)[type]
        found = next((x for x in candidates if re.match(pattern, x)), None)
        if found:
            return os.path.join(dir_path, found)
        # Bail when we hit a fork in the directory tree.
        if len(dir_names) > 1 or file_names:
            return


def guess_name(path):

    path = re.sub(r'[#?].+$', '', path) # Query strings and fragments.
    path = re.sub(r'(\.[\w-]+)+$', '', path) # Extensions.
    path = re.sub(r'([._-])v?\d+.*$', '', path) # Version numbers.
    path = re.sub(r'([._-])[._-]+', r'\1', path) # Collapse punctuation.

    part_iter = reversed(re.split(r'[@:/]', path)) # Split!
    part_iter = (re.sub(r'(^\W+|\W+$)', '', x) for x in part_iter) # Strip outer punctuation.
    part_iter = (x for x in part_iter if x) # Skip empties.

    return next(part_iter).lower()


def envsplit(value):
    return value.split(':') if value else []

def envjoin(*values):
    return ':'.join(x for x in values if x)


def guess_environ(paths, sources=None, use_current=True):

    if isinstance(paths, basestring):
        paths = [paths]

    if sources is None:
        sources = []
    elif isinstance(sources, dict):
        sources = [sources]
    else:
        sources = list(existing)

    if use_current:
        sources.append(os.environ)

    environ = {}   
    sources.insert(0, environ)

    def existing(key):
        for source in sources:
            try:
                return source[key]
            except KeyError:
                pass

    for path in reversed(paths):

        bin = os.path.join(path, 'bin')
        if os.path.exists(bin):
            environ['PATH'] = envjoin(bin, existing('PATH'))

        for bits in '', '64':
            lib = os.path.join(path, 'lib' + bits)
            if os.path.exists(lib):
                name = 'DYLD_LIBRARY_PATH' if sys.platform == 'darwin' else 'LD_LIBRARY_PATH'
                environ[name] = envjoin(lib, existing(name))
                site_packages = os.path.join(lib, 'python%d.%d' % sys.version_info[:2], 'site-packages')
                if os.path.exists(site_packages):
                    environ['PYTHONPATH'] = envjoin(site_packages, existing('PYTHONPATH'))

    return environ


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


def style_note(heading, msg='', detail=''):
    return '%s%s%s' % (
        style(heading, 'blue', bold=True),
        ' ' + style(msg, bold=True) if msg else '',
        ' ' + detail if detail else ''
    )

def style_error(msg, detail=''):
    return '%s %s%s' % (
        style('Error:', 'red', bold=True),
        style(msg, bold=True),
        detail and ' ' + detail
    )

def style_warning(msg, detail=''):
    return '%s %s%s' % (
        style('Warning:', 'yellow', bold=True),
        style(msg, bold=True),
        detail and ' ' + detail
    )


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
