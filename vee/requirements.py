import argparse
import collections
import datetime
import fnmatch
import json
import os
import re
import re
import shlex
import socket
import sys

from vee import log
from vee.cli import style
from vee.exceptions import AlreadyInstalled, CliMixin
from vee.package import Package, requirement_parser, RequirementParseError
from vee.utils import cached_property, guess_name





class Envvar(tuple):

    def __new__(cls, name, value):
        return super(Envvar, cls).__new__(cls, (name, value))

    @property
    def name(self):
        return self[0]

    @property
    def value(self):
        return self[1]

    def __str__(self):
        return '%s=%s' % self


class Header(object):

    def __init__(self, name, value):
        self.name = '-'.join(x.title() for x in name.split('-'))
        self.value = value

    def __str__(self):
        return '%s: %s' % (self.name, self.value)


class Control(object):

    def __init__(self, type_, expr):
        self.type = type_
        self.expr = expr

    def __repr__(self):
        return 'Control(%r, %r)' % (self.type, self.expr)

    def __str__(self):
        return '%% %s%s%s%s' % (
            self.type,
            ' ' if self.expr else '',
            self.expr,
            ':' if self.expr else '',
        )


class RequirementItem(object):

    def __init__(self, value, prefix='', suffix='', filename=None, lineno=None):
        self.value    = value
        self.prefix   = prefix or ''
        self.suffix   = suffix or ''
        self.filename = filename or None
        self.lineno   = lineno or None

    def __getattr__(self, name):
        return getattr(self.value, name)


class Requirements(collections.MutableSequence):

    def __init__(self, args=None, file=None, home=None, env_repo=None):

        self._items = []

        self.home = home
        self.env_repo = env_repo

        self._cumulative_environ = {}
        self.headers = {}

        if isinstance(args, basestring):
            args = [args]
        if args:
            self.parse_args(args)
        if file:
            self.parse_file(file)

    def _coerce(self, value, args=()):
        
        # This is the older format, and might still be used in some places.
        if isinstance(value, tuple) and len(value) == 3:
            if args:
                raise ValueError("RequirementItem 3-tuple cannot have extra args.", value, args)
            args = (value[0], value[2])
            value = value[1]

        if isinstance(value, RequirementItem):
            if args:
                raise ValueError("Cannot pass RequirementItem with extra args.", value, args)
            return value

        if isinstance(value, (Envvar, Header, Control, Package)):
            return RequirementItem(value, *args)

        if value:
            raise ValueError('Non-false value not of Envvar, Header, Control, or Package.', value)

        return RequirementItem(None, *args)

    # Sequence ABC methods.
    def __getitem__(self, index):
        return self._items[index]
    def __setitem__(self, index, value):
        self._items[index] = self._coerce(value)
    def __delitem__(self, index):
        del self._items[index]
    def __len__(self):
        return len(self._items)
    def append(self, value, *args):
        self._items.append(self._coerce(value, args))
    def insert(self, index, value, *args):
        self._items.insert(index, self._coerce(value, args))

    def parse_args(self, args):

        remaining = args
        while remaining:
            args, remaining = requirement_parser.parse_known_args(remaining)
            if args.url.endswith('.txt'):
                self.parse_file(args.url)
            else:
                self.append(('', Package(args, home=self.home), ''))

        self._guess_names()

    def parse_file(self, source, filename=None):
        
        if source == '-':
            filename = filename or '<stdin>'
            source = sys.stdin
        elif isinstance(source, basestring):
            filename = filename or source
            source = open(source, 'r')

        def append(x):
            self.append(RequirementItem(x, prefix, suffix, filename, line_i + 1))

        line_iter = iter(source)
        for line_i, line in enumerate(line_iter):

            line = line.rstrip()
            while line.endswith('\\'):
                line = line[:-1] + next(line_iter).rstrip()

            m = re.match(r'^(\s*)([^#]*?)(\s*#.*)?$', line)
            prefix, spec, suffix = m.groups()

            if not spec:
                append('')
                continue

            # Note: This will freak out with colons in comments.
            # TODO: Pull parsing from PyHAML.
            m = re.match(r'^%\s*(if|elif|else|endif)\s*(.*?):?\s*$', spec)
            if m:
                type_, expr = m.groups()
                append(Control(type_, expr))
                continue

            m = re.match(r'^(\w+)=(\S.*)$', spec)
            if m:
                name, value = m.groups()
                self._cumulative_environ[name] = value
                append(Envvar(name, value))
                continue

            m = re.match(r'^([\w-]+): (\S.*)$', spec)
            if m:
                header = Header(*m.groups())
                self.headers[header.name] = header
                append(header)
                continue

            try:
                pkg = Package(spec, home=self.home)
            except RequirementParseError as e:
                log.warning('parse error: %s' % e)
                self.append(('', '', '# RequirementParseError: %s' % e.args))
                self.append(('', '', '# ' + line.strip()))
                continue
            for k, v in self._cumulative_environ.iteritems():
                pkg.base_environ.setdefault(k, v)
            append(pkg)

        self._guess_names()

    def _guess_names(self, strict=True):
        """Guess names for every requirement which does not already have one.

        This mutates the requirements as it goes; if it fails then some
        requirements will have already had their name set.

        """

        names = set()
        to_guess = []

        # First pass: the explicitly named.
        for req in self.iter_packages():

            if not req.name:
                to_guess.append(req)
                continue

            if req.name.lower() in names:
                raise ValueError('name collision; please rename one of the %rs' % req.name)
            names.add(req.name.lower())

        # Second pass; the rest.
        for req in to_guess:
            name = guess_name(req.url)
            if name.lower() in names:
                if strict:
                    raise ValueError('name collision; please set name for one of the %rs' % name)
            else:
                names.add(name.lower())
                req.name = name

    def iter_packages(self, eval_control=True):

        include_stack = [True]
        control_namespace = {
            'fnmatch': fnmatch,
            'os': os,
            're': re,
            'socket': socket,
            'sys': sys,
            'OSX': sys.platform == 'darwin',
            'MACOS': sys.platform == 'darwin',
            'LINUX': sys.platform.startswith('linux'),
        }

        for item in self:

            el = item.value # TODO: Refactor.

            if eval_control and isinstance(el, Control):

                # The "if" stack is always two values: have any run, and should this run?
                if el.type == 'if':
                    do_this = bool(eval(el.expr, control_namespace))
                    include_stack.extend((do_this, do_this))
                elif el.type == 'elif':
                    include_stack.pop()
                    done_one = include_stack.pop()
                    do_this = False if done_one else bool(eval(el.expr, control_namespace))
                    include_stack.extend((done_one or do_this, do_this))
                elif el.type == 'else':
                    include_stack.pop()
                    done_one = include_stack.pop()
                    do_this = not done_one
                    include_stack.extend((True, do_this))
                elif el.type == 'endif':
                    include_stack.pop()
                    include_stack.pop()

                else:
                    raise ValueError('unknown control type %r' % el.type)

            if eval_control and not all(include_stack):
                continue

            if isinstance(el, Package):
                yield el

    def get_header(self, name):
        for item in self:
            el = item.value
            if isinstance(el, Header) and el.name.lower() == name.lower():
                return el.value
        raise KeyError(name)

    def set_header(self, name, value):
        for item in self:
            el = item.value
            if isinstance(el, Header) and el.name.lower() == name.lower():
                el.value = value
                return
        self.add_header(name, value)

    def add_header(self, name, value):
        for i, item in enumerate(self):
            el = item.value
            if not isinstance(el, Header):
                break
        header = Header(name, value)
        self.insert(i, RequirementItem(header))
        return header

    def iter_dump(self, freeze=False):

        # We track the state of the environment as we progress, and don't
        # include envvars in each requirement if they exactly match those
        # in the current state.
        environ = {}

        for item in self:

            # TODO: Refactor.
            element = item.value

            if isinstance(element, Envvar):
                environ[element.name] = element.value

            if isinstance(element, Package):

                req = element = (element.freeze() if freeze else element.copy())

                # We don't need a name if it matches the guessed version.
                if req.name and req.name == guess_name(req.url):
                    req.name = None

                # Strip out anything in the base environment which matches.
                for k, v in environ.iteritems():
                    if req.base_environ.get(k) == v:
                        del req.base_environ[k]

            yield '%s%s%s\n' % (item.prefix or '', element or '', item.suffix or '')



if __name__ == '__main__':

    import sys

    from vee.home import Home

    reqs = Requirements(Home())
    reqs.parse_args(sys.argv[1:])

    print ''.join(reqs.iter_dump())



