# encoding: utf-8

import contextlib
import re
import sys

from vee.globals import Stack


class StreamStyler(object):

    def __init__(self, stream, config=None):
        self._stream = stream
        self._config = config
        self._newline = True

    def write(self, to_write):
        config = self._config or _config_stack[-1]
        nl = self._newline
        for chunk in to_write.splitlines(True):
            
            if nl:
                chunk = config.indent + chunk
            nl = chunk.endswith('\n')

            if config.style:
                chunk = style(chunk, **config.style)

            self._stream.write(chunk)
        
        self._newline = nl

    def flush(self):
        self._stream.flush()





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


def strip_ansi(x):
    return re.sub(r'%s[\d;,]+[a-zA-Z]' % re.escape(CSI), '', x)


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
    if isinstance(c, str):
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


def style_note(heading, msg='', detail=''):
    return '%s%s%s' % (
        style(heading, 'blue'),
        ' ' + msg if msg else '',
        ' ' + detail if detail else ''
    )

def style_error(msg, detail=''):
    return '%s %s%s' % (
        style('Error:', 'red'),
        ' ' + msg if msg else '',
        ' ' + detail if detail else ''
    )

def style_warning(msg, detail=''):
    return '%s %s%s' % (
        style('Warning:', 'yellow'),
        ' ' + msg if msg else '',
        ' ' + detail if detail else ''
    )


if __name__ == '__main__':

    print('ANSI Styles')
    for i in xrange(1, 108):
        print(CSI + '0m' + CSI + str(i) + 'm' + ('%03d' % i) + CSI + '0m', end=' ')
        if i % 10 == 0:
            print()
    print()
    print()

    print('ANSI Colours')
    swatches = (('Normal', dict()),
                ('Faint',  dict(faint=True)),
                ('Bright', dict(bright=True)),
                ('Bold',   dict(bold=True)),
               )
    for title, _ in swatches:
        print('%-32s' % title, end=' ')
    print()
    for bg in sorted(_colour_codes.values()):
        for _, kwargs in swatches:
            for fg in sorted(_colour_codes.values()):
                print(colour(' %d%d' % (fg, bg), fg, bg, **kwargs), end=' ')
            print(colour(reset=True), end=' ')
        print(colour(reset=True))
    print()

    print('216 Colours')
    for r in xrange(0, 6):
        for g in xrange(0, 6):
            for b in xrange(0, 6):
                print(colour(u'◉ R%dG%dB%d' % (r, g, b), fg=(r, g, b), reset=True), end=' ')
            print(' ')
    print()

    print('Grays')
    for g in xrange(0, 24):
        print(colour('%02d' % g, fg=(g, ), reset=True), end=' ')
    print()
    for g in xrange(0, 24):
        print(colour('%02d' % g, bg=(g, ), reset=True), end=' ')
    print()
    print()

    exit()

    print('24-bit Colours')
    for r in xrange(0, 256, 256/8):
        for g in xrange(0, 256, 256/8):
            for b in xrange(0, 256, 256/8):
                print(colour('%02X%02X%02X' % (r, g, b), fg=(r, g, b), reset=True), end=' ')
            print()
    print()
