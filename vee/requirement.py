import argparse
import datetime
import os
import re
import shlex
import json

from vee.exceptions import AlreadyInstalled, CliException
from vee.utils import style


class RequirementParseError(CliException):
    pass


class _Parser(argparse.ArgumentParser):

    def error(self, message):
        raise RequirementParseError(message)


class _configAction(argparse.Action):

    @property
    def default(self):
        return []
    @default.setter
    def default(self, v):
        pass

    def __call__(self, parser, namespace, values, option_string=None):
        res = getattr(namespace, self.dest)
        for value in values:
            res.extend(value.split(','))


class _EnvironmentAction(argparse.Action):

    @property
    def default(self):
        return {}
    @default.setter
    def default(self, v):
        pass

    def __call__(self, parser, namespace, values, option_string=None):
        res = getattr(namespace, self.dest)
        for value in values:
            parts = re.split(r'(?:^|,)(\w+)=', value)
            for i in xrange(1, len(parts), 2):
                res[parts[i]] = parts[i + 1]


class Requirement(object):

    _arg_parser = _Parser(add_help=False)
    _arg_parser.add_argument('-t', '--type')
    _arg_parser.add_argument('-n', '--name')
    _arg_parser.add_argument('-r', '--revision')
    _arg_parser.add_argument('-f', '--force-fetch', action='store_true', help='always fetch git repos')
    _arg_parser.add_argument('-e', '--environ', nargs='*', action=_EnvironmentAction)
    _arg_parser.add_argument('-c', '--config', nargs='*', action=_configAction,
        help='args to pass to `./configure`, `python setup.py`, `brew install`, etc..')
    _arg_parser.add_argument('--install-name')
    _arg_parser.add_argument('--build-subdir')
    _arg_parser.add_argument('--install-prefix')
    _arg_parser.add_argument('url')

    def __init__(self, args=None, home=None, **kwargs):

        if args and kwargs:
            raise ValueError('specify either args OR kwargs')

        if args:

            # If there are args, parse them.
            if isinstance(args, basestring):
                args = shlex.split(args)
            if isinstance(args, (list, tuple)):
                self._arg_parser.parse_args(args, namespace=self)
            else:
                raise TypeError('args must be in (str, list, tuple); got %s' % args.__class__)

        else:

            for action in self._arg_parser._actions:
                name = action.dest
                if name in kwargs:
                    setattr(self, name, kwargs[name])

        # Manual args.
        self.home = home

        # Extract the manager type. Usually this is of the form:
        # type+specification. Otherwise we assume it is a simple URL or file.
        if not self.type:
            m = re.match(r'^(\w+)\+(.+)$', self.url)
            if m:
                self.type = m.group(1)
                self.url = m.group(2)
            elif re.match(r'^https?://', self.url):
                self.type = 'http'
            else:
                self.type = 'file'

        self.package = self.home.get_package(requirement=self)

    def to_kwargs(self):
        kwargs = {}
        for action in self._arg_parser._actions:
            name = action.dest
            value = getattr(self, name)
            if value:
                kwargs[name] = value
        return kwargs

    def to_json(self):
        return json.dumps(self.to_kwargs(), sort_keys=True)

    def to_args(self):

        argsets = []
        for action in self._arg_parser._actions:

            name = action.dest
            if name in ('type', 'url'):
                continue

            value = getattr(self, name)
            if not value:
                continue

            if action.__class__.__name__ == '_StoreTrueAction': # Gross.
                if value:
                    argsets.append(['--%s' % name])
                continue

            if isinstance(value, dict):
                value = ','.join('%s=%s' % (k, v) for k, v in sorted(value.iteritems()))
            if isinstance(value, (list, tuple)):
                value = ','.join(value)

            # Shell escape!
            if re.search(r'\s', value):
                value = "'%s'" % value.replace("'", "''")

            argsets.append(['--%s=%s' % (name.replace('_', '-'), str(value))])

        args = [
            (self.type or '') +
            ('+' if self.type else '') +
            self.url
        ]
        for argset in sorted(argsets):
            args.extend(argset)
        return args

    def __str__(self):
        return ' '.join(self.to_args())

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def _reinstall_check(self, force):
        if self.package.installed:
            if force:
                self.package.uninstall()
            else:
                raise AlreadyInstalled(str(self))

    def install(self, force=False):

        if not self.force_fetch:
            self._reinstall_check(force)

        self.package.fetch()
        self._reinstall_check(force) # We may only know once we have fetched.
    
        self.package.extract()
        self._reinstall_check(force) # Packages may self-describe.

        self.package.build()
        self.package.install()

        # Record it!
        self.package.db_id()





