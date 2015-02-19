import argparse
import datetime
import os
import re
import shlex

from vee.exceptions import AlreadyInstalled, CliException


class RequirementParseError(CliException):
    pass


class _Parser(argparse.ArgumentParser):

    def error(self, message):
        raise RequirementParseError(message)


class _ConfigurationAction(argparse.Action):

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
    _arg_parser.add_argument('-c', '--configuration', nargs='*', action=_ConfigurationAction,
        help='args to pass to `./configure`, `python setup.py`, `brew install`, etc..')
    _arg_parser.add_argument('--install-name')
    _arg_parser.add_argument('--install-subdir')
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

    def resolve_existing(self):
        """Check against the index to see if this was already installed."""

        if self.package._index_id is not None:
            raise ValueError('requirement already in index')

        cur = self.home.index.cursor()

        clauses = ['type = ?', 'url = ?']
        values = [self.type, self.url]
        for attr in ('name', 'revision'):
            if getattr(self, attr):
                clauses.append('%s = ?' % attr)
                values.append(getattr(self, attr))
        for attr in ('_package_name', '_build_name', '_install_name'):
            if getattr(self.package, attr):
                clauses.append('%s = ?' % attr.strip('_'))
                values.append(getattr(self.package, attr))

        row = cur.execute('''
            SELECT * FROM packages
            WHERE %s
            ORDER BY created_at DESC
            LIMIT 1
        ''' % ' AND '.join(clauses), values).fetchone()

        if not row:
            return

        # Everything below either already matches or was unset.
        self.package._index_id = row['id']
        self.name = row['name']
        self.revision = row['revision']
        self.package._package_name = row['package_name']
        self.package._build_name = row['build_name']
        self.package._install_name = row['install_name']
        if (self.package.package_path != row['package_path'] or
            self.package.build_path != row['build_path'] or
            self.package.install_path != row['install_path']
        ):
            raise RuntimeError('indexed paths dont match')

        return True



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
        self.package.index_id()





