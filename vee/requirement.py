import argparse
import datetime
import json
import os
import re
import shlex

from vee.cli import style
from vee.exceptions import AlreadyInstalled, CliMixin
from vee.packages import make_package
from vee.utils import cached_property


class RequirementParseError(CliMixin, ValueError):
    pass


class _requirement_parser(argparse.ArgumentParser):

    def error(self, message):
        raise RequirementParseError(message)


class _configAction(argparse.Action):

    @property
    def default(self):
        return []
    @default.setter
    def default(self, v):
        pass

    def __call__(self, requirement_parser, namespace, values, option_string=None):
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

    def __call__(self, requirement_parser, namespace, values, option_string=None):
        res = getattr(namespace, self.dest)
        for value in values:
            parts = re.split(r'(?:^|,)(\w+)=', value)
            for i in xrange(1, len(parts), 2):
                res[parts[i]] = parts[i + 1]



requirement_parser = _requirement_parser(add_help=False)

requirement_parser.add_argument('-n', '--name')
requirement_parser.add_argument('-r', '--revision')

requirement_parser.add_argument('-e', '--environ', nargs='*', action=_EnvironmentAction)
requirement_parser.add_argument('-c', '--config', nargs='*', action=_configAction, help='args to pass to `./configure`, `python setup.py`, `brew install`, etc..')

requirement_parser.add_argument('--make-install', action='store_true', help='do `make install`')

requirement_parser.add_argument('--install-name')
requirement_parser.add_argument('--build-subdir')
requirement_parser.add_argument('--install-prefix')

requirement_parser.add_argument('url')



class Requirement(object):


    def __init__(self, args=None, home=None, **kwargs):

        if args and kwargs:
            raise ValueError('specify either args OR kwargs')

        if args:
            if isinstance(args, basestring):
                args = shlex.split(args)
            if isinstance(args, (list, tuple)):
                requirement_parser.parse_args(args, namespace=self)
            elif isinstance(args, argparse.Namespace):
                for action in requirement_parser._actions:
                    name = action.dest
                    setattr(self, name, getattr(args, name))
            else:
                raise TypeError('args must be in (str, list, tuple); got %s' % args.__class__)

        else:
            for action in requirement_parser._actions:
                name = action.dest
                setattr(self, name, kwargs.get(name, action.default))

        # Manual args.
        self.home = home

    @cached_property
    def package(self):
        return make_package(self, self.home)

    def to_kwargs(self):
        kwargs = {}
        for action in requirement_parser._actions:
            name = action.dest
            value = getattr(self, name)
            if value != action.default: # Easily wrong.
                kwargs[name] = value
        return kwargs

    def to_json(self):
        return json.dumps(self.to_kwargs(), sort_keys=True)

    def to_args(self):

        argsets = []
        for action in requirement_parser._actions:

            name = action.dest
            if name in ('type', 'url'):
                continue

            option_str = action.option_strings[-1]

            value = getattr(self, name)
            if not value:
                continue

            if action.__class__.__name__ == '_StoreTrueAction': # Gross.
                if value:
                    argsets.append([option_str])
                continue

            if isinstance(value, dict):
                value = ','.join('%s=%s' % (k, v) for k, v in sorted(value.iteritems()))
            if isinstance(value, (list, tuple)):
                value = ','.join(value)

            # Shell escape!
            if re.search(r'\s', value):
                value = "'%s'" % value.replace("'", "''")

            argsets.append(['%s=%s' % (option_str, str(value))])

        args = [self.url]
        for argset in sorted(argsets):
            args.extend(argset)
        return args

    def __str__(self):
        return ' '.join(self.to_args())

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))


    def auto_install(self, **kwargs):
        self.package.auto_install(**kwargs)






