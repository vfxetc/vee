from __future__ import print_function

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
from vee.utils import cached_property, guess_name, makedirs


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


class Expression(object):

    def __init__(self, source, type='eval'):
        self.source = source
        self.type = type

    def __repr__(self):
        if self.type == 'eval':
            return 'Expression(%r)' % self.source
        else:
            return 'Expression(%r, type=%r)' % (self.source, self.type)

    def __str__(self):
        return '%% %s %s' % (self.type, self.source)

    def __call__(self, namespace):
        eval(compile(self.source, '<vee>', 'exec'), namespace, namespace)


class Include(object):

    def __init__(self, path, requirements):
        self.path = path
        self.requirements = requirements

    def __str__(self):
        return '% include {}'.format(self.path)


class RequirementItem(object):

    def __init__(self, value, prefix='', suffix='', filename=None, lineno=None):
        self.value    = value
        self.prefix   = prefix or ''
        self.suffix   = suffix or ''
        self.filename = filename or None
        self.lineno   = lineno or None

    def __getattr__(self, name):
        return getattr(self.value, name)

    @property
    def is_package(self):
        return isinstance(self.value, Package)

    @property
    def is_include(self):
        return isinstance(self.value, Include)


class Manifest:

    def __init__(self, args=None, file=None, home=None, repo=None):

        if not home:
            raise ValueError("Manifest requires home")

        self._items = []
        self._packages = {}

        self.filename = None
        self.home = home
        self.repo = repo

        self._cumulative_environ = {}
        self.headers = {}

        if isinstance(args, str):
            args = [args]
        if args:
            self.parse_args(args)
        if file:
            self.parse_file(file)

    def _coerce(self, value, args=()):

        if isinstance(value, RequirementItem):
            if args:
                raise ValueError("cannot pass RequirementItem with extra args.", value, args)
            return value

        if isinstance(value, (Envvar, Header, Control, Package, Include)):
            return RequirementItem(value, *args)

        if value:
            raise ValueError("unexpected type: got {} {!r}".format(type(value), value))

        return RequirementItem(None, *args)

    def _append(self, value, *args):
        item = self._coerce(value, args)
        if isinstance(item.value, Package):
            self._register_package(item.value)
        self._items.append(item)

    def _insert(self, index, value, *args):
        item = self._coerce(value, args)
        if isinstance(item.value, Package):
            self._register_package(item.value)
        self._items.insert(index, item)

    def _register_package(self, pkg):
        if pkg.name in self._packages:
            raise ValueError("name collision; please rename one of {!r}".format(pkg.name))
        self._packages[pkg.name] = pkg

    def get(self, name):
        """Get the named :class:`Package`, or ``None``."""
        return self._packages.get(name)

    def parse_args(self, args):

        if isinstance(args, str):
            args = shlex.split(args)

        remaining = args
        while remaining:
            args, remaining = requirement_parser.parse_known_args(remaining)
            if args.url.endswith('.txt'):
                self.parse_file(args.url)
            else:
                pkg = Package(args, home=self.home, context=self)
                self._append(pkg)

    def parse_file(self, source, filename=None, alt_open=None, _depth=0):
        
        open_ = alt_open or open

        if source == '-':
            filename = filename or '<stdin>'
            source = sys.stdin
        elif isinstance(source, str):
            filename = filename or source
            source = open_(source)

        self.filename = self.filename or filename

        def append(x):
            self._append(RequirementItem(x, prefix, suffix, filename, line_i + 1))

        line_iter = iter(source)
        for line_i, line in enumerate(line_iter):

            line = line.rstrip()
            while line.endswith('\\'):
                line = line[:-1] + next(line_iter).rstrip()

            m = re.match(r'^(\s*)([^#]*?)(\s*#.*)?$', line)
            prefix, spec, suffix = m.groups()

            if not spec:
                append(None)
                continue

            # Note: This will freak out with colons in comments.
            # TODO: Pull parsing from PyHAML.
            m = re.match(r'^%\s*(if|elif|else|endif)\s*(.*?):?\s*$', spec)
            if m:
                type_, expr = m.groups()
                append(Control(type_, expr))
                continue

            m = re.match(r'^%\s*(set|eval|expr)\s+(.+?)\s*$', spec)
            if m:
                type_, source = m.groups()
                append(Expression(source, type_))
                continue

            m = re.match(r'^%\s*include\s+(.+?)\s*$', spec)
            if m:
                raw_path = m.group(1)
                path = os.path.normpath(raw_path).strip('/')
                if raw_path != path:
                    raise ValueError("Malformed include path.", raw_path)
                if self.filename:
                    path = os.path.join(os.path.dirname(self.filename), path)
                other = Manifest(repo=self.repo, home=self.home)
                other.parse_file(path, alt_open=alt_open, _depth=_depth + 1)
                append(Include(raw_path, other))
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
                self._append('', '', '# RequirementParseError: %s' % e.args)
                self._append('', '', '# ' + line.strip())
                continue
            for k, v in self._cumulative_environ.items():
                pkg.base_environ.setdefault(k, v)
            append(pkg)

        if not _depth:
            self._load_metas()

    def _load_metas(self):
        """Find ``Package`` class in `packages/{name}.py` file for each package.

        Any found class will be instatiated and set to :attr:`Package.meta`.

        """

        # We're fully in memory.
        if not self.filename:
            return

        base = os.path.join(os.path.dirname(self.filename), 'packages')
        if not os.path.exists(base):
            return

        for pkg in self.iter_packages():

            # Already done.
            if pkg.meta is not None:
                continue

            path = os.path.join(base, pkg.name + '.py')
            if not os.path.exists(path):
                continue

            namespace = {'__file__': path}
            with open(path, 'rb') as fh:
                source = fh.read()
            try:
                exec(compile(source, path, 'exec'), namespace, namespace)
            except Exception as e:
                raise ValueError("error while loading package meta in {}".format(path)) from e

            cls = namespace.get('Package')
            if not isinstance(cls, type):
                raise ValueError("no Package class defined in {}".format(path))

            pkg.meta = cls

    def iter_packages(self, eval_control=True, locals_=None):

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
        if locals_:
            control_namespace.update(locals_)

        for item in self._items:

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

            if isinstance(el, Expression):
                el(control_namespace)
                continue

            if isinstance(el, Package):
                yield el

            elif isinstance(el, Include):
                for x in el.requirements.iter_packages(eval_control, locals_=control_namespace):
                    yield x

    def get_header(self, name):
        for item in self:
            el = item.value
            if isinstance(el, Header) and el.name.lower() == name.lower():
                return el.value
        raise KeyError(name)

    def set_header(self, name, value):
        for item in self._items:
            el = item.value
            if isinstance(el, Header) and el.name.lower() == name.lower():
                el.value = value
                return
        self.add_header(name, value)

    def add_header(self, name, value):
        for i, item in enumerate(self._items):
            el = item.value
            if not isinstance(el, Header):
                break
        header = Header(name, value)
        self._items.insert(i, RequirementItem(header))
        return header

    def iter_dump(self, freeze=False):

        # We track the state of the environment as we progress, and don't
        # include envvars in each requirement if they exactly match those
        # in the current state.
        environ = {}

        for item in self._items:

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
                for k, v in environ.items():
                    if req.base_environ.get(k) == v:
                        del req.base_environ[k]

            yield '%s%s%s\n' % (item.prefix or '', element or '', item.suffix or '')

    def dump(self, path, recurse=True):

        paths = [path]

        tmp = path + '.tmp'
        with open(tmp, 'w') as fh:
            for line in self.iter_dump():
                fh.write(line)
        os.rename(tmp, path)

        if not recurse:
            return

        for item in self._items:
            if not item.is_include:
                continue
            include = item.value
            req_set = include.requirements
            sub_path = os.path.join(os.path.dirname(path), include.path)
            makedirs(os.path.dirname(sub_path))
            paths.extend(req_set.dump(sub_path))

        return paths

if __name__ == '__main__':

    import sys

    from vee.home import Home

    manifest = Manifest(home=Home())
    manifest.parse_args(sys.argv[1:])

    print(''.join(manifest.iter_dump()))



