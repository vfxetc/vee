import argparse
import datetime
import json
import os
import re
import re
import shlex
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


class Requirements(list):

    def __init__(self, args=None, file=None, home=None):

        self.home = home
        self._cumulative_environ = {}
        self.headers = {}

        if isinstance(args, basestring):
            args = [args]
        if args:
            self.parse_args(args)
        if file:
            self.parse_file(file)

    def parse_args(self, args):

        remaining = args
        while remaining:
            args, remaining = requirement_parser.parse_known_args(remaining)
            if args.url.endswith('.txt'):
                self.parse_file(args.url)
            else:
                self.append(('', Package(args, home=self.home), ''))

        self._guess_names()

    def parse_file(self, source):
        
        if source == '-':
            source = sys.stdin
        elif isinstance(source, basestring):
            source = open(source, 'r')

        line_iter = iter(source)
        for line in line_iter:

            line = line.rstrip()
            while line.endswith('\\'):
                line = line[:-1] + next(line_iter).rstrip()

            m = re.match(r'^(\s*)([^#]*?)(\s*#.*)?$', line)
            before, spec, after = m.groups()
            before = before or ''
            after = after or ''

            if not spec:
                self.append((before, '', after))
                continue

            # Note: This will freak out with colons in comments.
            # TODO: Pull parsing from PyHAML.
            m = re.match(r'^%\s*(if|elif|else|endif)\s*(.*?):?\s*$', spec)
            if m:
                type_, expr = m.groups()
                self.append((before, Control(type_, expr), after))
                continue

            m = re.match(r'^(\w+)=(\S.*)$', spec)
            if m:
                name, value = m.groups()
                self._cumulative_environ[name] = value
                self.append((before, Envvar(name, value), after))
                continue

            m = re.match(r'^([\w-]+): (\S.*)$', spec)
            if m:
                header = Header(*m.groups())
                self.headers[header.name] = header
                self.append((before, header, after))
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
            self.append((before, pkg, after))

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
            're': re,
            'sys': sys,
            'os': os,
            'OSX': sys.platform == 'darwin',
            'MACOS': sys.platform == 'darwin',
            'LINUX': sys.platform.startswith('linux'),
        }

        for _, el, _ in self:

            if eval_control and isinstance(el, Control):
                if el.type == 'if':
                    include_stack.append(bool(eval(el.expr, control_namespace)))
                elif el.type == 'elif':
                    include_stack.pop()
                    include_stack.append(bool(eval(el.expr, control_namespace)))
                elif el.type == 'else':
                    prev = include_stack.pop()
                    include_stack.append(not prev)
                elif el.type == 'endif':
                    include_stack.pop()
                else:
                    raise ValueError('unknown control type %r' % el.type)

            if eval_control and not all(include_stack):
                continue

            if isinstance(el, Package):
                yield el

    def get_header(self, name):
        for _, el, _ in self:
            if isinstance(el, Header) and el.name.lower() == name.lower():
                return el.value
        raise KeyError(name)

    def set_header(self, name, value):
        for _, el, _ in self:
            if isinstance(el, Header) and el.name.lower() == name.lower():
                el.value = value
                return
        self.add_header(name, value)

    def add_header(self, name, value):
        for i, (_, el, _) in enumerate(self):
            if not isinstance(el, Header):
                break
        header = Header(name, value)
        self.insert(i, ('', header, ''))
        return header

    def iter_dump(self, freeze=False):

        # We track the state of the environment as we progress, and don't
        # include envvars in each requirement if they exactly match those
        # in the current state.
        environ = {}

        for before, element, after in self:

            if isinstance(element, Envvar):
                environ[element.name] = element.value

            if isinstance(element, Package):
                if freeze:
                    req = element = element.package.freeze(environ=False)
                else:
                    req = element
                if req.name and req.name == guess_name(req.url):
                    req.name = None
                for k, v in environ.iteritems():
                    if req.environ.get(k) == v:
                        del req.environ[k]
                    if req.base_environ.get(k) == v:
                        del req.base_environ[k]

            yield '%s%s%s\n' % (before or '', element, after or '')



if __name__ == '__main__':

    import sys

    from vee.home import Home

    reqs = Requirements(Home('/usr/local/vee'))
    reqs.parse_args(sys.argv[1:])

    print ''.join(reqs.iter_dump())



