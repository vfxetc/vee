import argparse
import datetime
import os
import re
import shlex

from vee.exceptions import AlreadyInstalled


class Requirement(object):

    arg_parser = argparse.ArgumentParser(add_help=False)
    arg_parser.add_argument('-n', '--name')
    arg_parser.add_argument('-r', '--revision')
    arg_parser.add_argument('-f', '--force-fetch', action='store_true', help='always fetch git repos')
    arg_parser.add_argument('-e', '--environ', action='append', default=[])
    arg_parser.add_argument('-c', '--configuration', help='args to pass to `./configure`, `python setup.py`, `brew install`, etc..')
    arg_parser.add_argument('--install-name')
    arg_parser.add_argument('--install-subdir')
    arg_parser.add_argument('url')


    def __init__(self, args, home=None):

        if isinstance(args, basestring):
            args = shlex.split(args)
        if isinstance(args, (list, tuple)):
            args = self.arg_parser.parse_args(args)
            
        # Extract the manager type. Usually this is of the form:
        # type+specification. Otherwise we assume it is a simple URL or file.
        m = re.match(r'^(\w+)\+(.+)$', args.url)
        if m:
            self.type = m.group(1)
            self.url = m.group(2)
        elif re.match(r'^https?://', args.url):
            self.type = 'http'
            self.url = args.url
        else:
            self.type = 'file'
            self.url = os.path.abspath(os.path.expanduser(args.url))

        self._args = args

        self.configuration = args.configuration
        self.install_name = args.install_name
        self.name = args.name
        self.revision = args.revision
        self.install_subdir = args.install_subdir
        self.force_fetch = args.force_fetch

        self.environ = {}
        for x in args.environ:
            parts = re.split(r'(?:^|,)(\w+)=', x)
            for i in xrange(1, len(parts), 2):
                self.environ[parts[i]] = parts[i + 1]

        self.home = home or args.home
        self.package = self.home.get_package(requirement=self)

        self._user_specification = str(self)

        self._index_id = None


    def __str__(self):
        args = []
        for name in (
            'force_fetch',
        ):
            value = getattr(self, name)
            if value:
                args.append('--%s' % name.replace('_', '-'))
        for name in (
            'configuration',
            'environ',
            'install_name',
            'install_subdir',
            'name',
            'revision',
        ):
            value = getattr(self, name)
            if value:
                if isinstance(value, dict):
                    value = ','.join('%s=%s' % (k, v) for k, v in sorted(value.iteritems()))
                if isinstance(value, (list, tuple)):
                    value = ','.join(value)
                args.append('--%s %s' % (name.replace('_', '-'), value))
        return (
            self.type +
            ('+' if self.type else '') +
            self.url +
            (' ' if args else '') +
            ' '.join(sorted(args))
        )

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def resolve_existing(self):
        """Check against the index to see if this was already installed."""

        if self._index_id is not None:
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
        self._index_id = row['id']
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

    def resolve_environ(self, source=None):

        source = (source or os.environ).copy()
        source['VEE'] = self.home.root

        diff = {}

        def rep(m):
            a, b, c, orig = m.groups()
            abc = a or b or c
            if abc:
                return source.get(abc, '')
            if orig:
                return source.get(k)

        for k, v in self.environ.iteritems():
            v = re.sub(r'\$\{(\w+)\}|\$(\w+)|%(\w+)%|(@)', rep, v)
            diff[k] = v

        return diff

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
        self.index_id()

    def index_id(self):
        if self._index_id is None:
            self.package._set_names(package=True, build=True, install=True)
            if not self.package.installed:
                raise ValueError('cannot index requirement that is not installed')
            cur = self.home.index.cursor()
            cur.execute('''
                INSERT INTO packages (created_at, abstract_requirement, concrete_requirement,
                                      type, url, name, revision, package_name, build_name,
                                      install_name, package_path, build_path, install_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [datetime.datetime.utcnow(), self._user_specification, str(self),
                  self.type, self.url, self.name, self.revision, self.package._package_name,
                  self.package._build_name, self.package._install_name, self.package.package_path,
                  self.package.build_path, self.package.install_path]
            )
            self._index_id = cur.lastrowid
        return self._index_id




