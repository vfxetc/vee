import argparse
import datetime
import fnmatch
import glob
import json
import os
import re
import shlex
import shutil
import sys

from vee._vendor import pkg_resources

from vee import libs
from vee import log
from vee.cli import style, style_note
from vee.database import DBObject, Column
from vee.exceptions import AlreadyInstalled, AlreadyLinked, CliMixin
from vee.pipeline.base import Pipeline
from vee.subproc import call
from vee.utils import cached_property, makedirs, linktree


class RequirementParseError(CliMixin, ValueError):
    pass


class _RequirementParser(argparse.ArgumentParser):
    def error(self, message):
        raise RequirementParseError(message)


class _ConfigAction(argparse.Action):

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



requirement_parser = _RequirementParser(add_help=False)

requirement_parser.add_argument('-n', '--name')
requirement_parser.add_argument('-r', '--revision')

requirement_parser.add_argument('--etag', help='identifier for busting caches')

requirement_parser.add_argument('--base-environ', nargs='*', action=_EnvironmentAction, help=argparse.SUPPRESS)
requirement_parser.add_argument('-e', '--environ', nargs='*', action=_EnvironmentAction)
requirement_parser.add_argument('-c', '--config', nargs='*', action=_ConfigAction, help='args to pass to `./configure`, `python setup.py`, `brew install`, etc..')

requirement_parser.add_argument('--make-install', action='store_true', help='do `make install`')

requirement_parser.add_argument('--install-name')
requirement_parser.add_argument('--build-subdir')
requirement_parser.add_argument('--install-prefix')

requirement_parser.add_argument('--relocate', help='how to relocate shared libs')
requirement_parser.add_argument('--hard-link', action='store_true', help='use hard links instead of copies')

requirement_parser.add_argument('url')


class Package(DBObject):

    """Abstraction of a package manager.

    Packages are instances for each :class:`Requirement`, such that they are
    able to maintain state about that specific requirement.

    """

    __tablename__ = 'packages'

    abstract_requirement = Column()

    concrete_requirement = Column()
    @concrete_requirement.persist
    def concrete_requirement(self):
        return self.freeze().to_json()

    package_type = Column()
    @package_type.persist
    def package_type(self):
        return self.pipeline.load('fetch').name

    build_type = Column()
    @build_type.persist
    def build_type(self):
        return self.pipeline.load('build').name

    url = Column()
    name = Column()
    revision = Column()
    etag = Column()
    package_name = Column()
    build_name = Column()
    install_name = Column()
    package_path = Column()
    build_path = Column()
    install_path = Column()

    def __init__(self, args=None, home=None, set=None, dev=False, **kwargs):

        super(Package, self).__init__()

        if args and kwargs:
            raise ValueError('specify either args OR kwargs')

        if isinstance(args, self.__class__):
            kwargs = args.to_kwargs()
            args = None
        elif isinstance(args, dict):
            kwargs = args
            args = None

        if args:
            if isinstance(args, basestring):
                args = shlex.split(args)
            if isinstance(args, (list, tuple)):
                try:
                    requirement_parser.parse_args(args, namespace=self)
                except RequirementParseError as e:
                    raise RequirementParseError("%s in %s" % (e.args[0], args))
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
        self.home = home # Must be first.
        self.abstract_requirement = self.to_json()
        self.dependencies = []
        self.set = set

        # Make sure to make copies of anything that is mutable.
        self.base_environ = self.base_environ.copy() if self.base_environ else {}
        self.environ = self.environ.copy() if self.environ else {}
        self.config = self.config[:] if self.config else []

        # Initialize other state not covered by the argument parser.
        self.link_id = None
        self.package_name = self.build_name = None
        self.package_path = self.build_path = self.install_path = None

        # Create the pipeline object.
        if dev:
            self.package_name = self.build_name = self.url
            self.package_path = self.build_path = self.url
            self.pipeline = Pipeline(self, ['init', 'inspect', 'develop'])
        else:
            self.pipeline = Pipeline(self, ['init', 'fetch', 'extract', 'inspect', 'build', 'install'])

        # Give the fetch pipeline step a chance to normalize the URL.
        self.pipeline.run_to('init')

    def to_kwargs(self):
        kwargs = {}
        for action in requirement_parser._actions:
            name = action.dest
            value = getattr(self, name)
            if value != action.default: # This is easily wrong.
                kwargs[name] = value
        return kwargs

    def to_json(self):
        return json.dumps(self.to_kwargs(), sort_keys=True)

    def to_args(self, exclude=set()):

        argsets = []
        for action in requirement_parser._actions:

            name = action.dest
            if name in ('type', 'url') or name in exclude:
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
        return ' '.join(self.to_args(exclude=('base_environ')))

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def freeze(self, environ=True):
        kwargs = self.to_kwargs()
        if environ:
            kwargs['environ'] = self.environ_diff
        return self.__class__(kwargs, home=self.home)

    def _resolve_environ(self, source=None):

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

        for e in (self.base_environ, self.environ):
            for k, v in self.environ.iteritems():
                v = re.sub(r'\$\{(\w+)\}|\$(\w+)|%(\w+)%|(@)', rep, v)
                diff[k] = v

        return diff

    _environ_diff = None

    @property
    def environ_diff(self):
        if self._environ_diff is None:
            self._environ_diff = self._resolve_environ()
            for k, v in sorted(self._environ_diff.iteritems()):
                old_v = os.environ.get(k)
                if old_v is not None:
                    v = v.replace(old_v, '@')
                v = v.replace(self.home.root, '$VEE')
                log.debug('%s %s=%s' % (
                    style('setenv', 'blue'), k, v
                ), verbosity=1)
        return self._environ_diff or {}

    def fresh_environ(self):
        environ = os.environ.copy()
        environ.update(self.environ_diff)
        return environ

    def _set_names(self, package=False, build=False, install=False):
        if (package or build or install) and self.package_name is None:
            if self.url:
                # Strip out the scheme.
                name = re.sub(r'^[\w._+-]+:', '', self.url)
                name = re.sub(r':?/+:?', '/', name)
                name = name.strip('/')
                self.package_name = name
        if (install or build) and self.install_name is None:
            if self.name and self.revision:
                self.install_name = '%s/%s' % (self.name, self.revision)
            else:
                self.install_name = self.package_name and re.sub(r'(\.(tar|gz|tgz|zip))+$', '', self.package_name)
        if build and self.build_name is None:
            self.build_name = self.install_name and ('%s/%s-%s' % (
                self.install_name,
                datetime.datetime.utcnow().strftime('%y%m%d%H%M%S'),
                os.urandom(4).encode('hex'),
            ))

    def _assert_names(self, **kwargs):
        self._set_names(**kwargs)
        for attr, value in kwargs.iteritems():
            if value and not getattr(self, '_%s_name' % attr):
                raise RuntimeError('%s name required' % attr)

    def _set_paths(self, package=False, build=False, install=False):
        self._set_names(package, build, install)
        if package:
            self.package_path = self.package_path or (self.package_name and self.home._abs_path('packages', self.package_name))
        if build:
            self.build_path   = self.build_path   or (self.build_name   and self.home._abs_path('builds',   self.build_name  ))
        if install:
            self.install_path = self.install_path or (self.install_name and self.home._abs_path('installs', self.install_name))

    def _assert_paths(self, **kwargs):
        self._set_paths(**kwargs)
        for attr, value in kwargs.iteritems():
            if value and not getattr(self, '%s_path' % attr):
                raise RuntimeError('%s path required' % attr)

    @property
    def build_path_to_install(self):
        return os.path.join(self.build_path, self.build_subdir or '').rstrip('/')

    @property
    def install_path_from_build(self):
        return os.path.join(self.install_path, self.install_prefix or '').rstrip('/')

    @property
    def fetch_type(self):
        return self.pipeline.load('fetch').name

    def _clean_build_path(self, makedirs=True):
        if self.build_path and os.path.exists(self.build_path):
            shutil.rmtree(self.build_path)
        if makedirs:
            os.makedirs(self.build_path)


    @property
    def installed(self):
        # self._assert_paths(install=True)
        # print 'installed', (self.id, self.install_name, self.install_path)
        return bool(
            self.install_path and # The path is set,
            os.path.isdir(self.install_path) and # it exists as a directory,
            os.listdir(self.install_path) # and it has contents.
        )

    def fetch(self):
        self.pipeline.run_to('fetch')

    def extract(self):
        self.pipeline.run_to('extract')

    def inspect(self):
        self.pipeline.run_to('inspect')

    def build(self):
        self.pipeline.run_to('build')

    def develop(self):
        self.pipeline.run_to('inspect')
        self.pipeline.run_to('develop')
    
    def install(self):
        """Install the build artifact into a final location."""

        # self._assert_paths(build=True, install=True)

        if self.installed:
            raise AlreadyInstalled('was already installed at %s' % self.install_path)

        self.pipeline.run_to('install')

        if self.relocate:
            log.info(style_note('Relocating'))
            libs.relocate(self.install_path,
                con=self.home.db.connect(),
                spec=self.relocate + ',SELF',
            )

        # Link into $VEE/opt.
        if self.name:
            opt_link = self.home._abs_path('opt', self.name)
            log.info(style_note('Linking to opt/%s' % self.name))
            if os.path.lexists(opt_link):
                os.unlink(opt_link)
            makedirs(os.path.dirname(opt_link))
            os.symlink(self.install_path, opt_link)

    def uninstall(self):
        # self._set_names(install=True)
        if not self.installed:
            raise RuntimeError('package is not installed')
        log.info(style_note('Uninstalling ', self.install_path))
        shutil.rmtree(self.install_path)

    def shared_libraries(self, rescan=False):
        self._assert_paths(install=True)
        if not self.installed:
            raise RuntimeError('cannot find libraries if not installed')
        if not self.id:
            # I'm not sure if this is a big deal, but I want to see when
            # it is happening.
            log.warning('Finding shared libraries before package is in database.')
        return libs.get_installed_shared_libraries(self.home.db.connect(), self.id_or_persist(), self.install_path, rescan)

    def link(self, env, force=False):
        self._assert_paths(install=True)
        frozen = self.freeze()
        if not force:
            self._assert_unlinked(env, frozen)
        log.info(style_note('Linking into %s' % env.name))
        env.link_directory(self.install_path)
        self._record_link(env)

    def _assert_unlinked(self, env, frozen=None):
        if not self.link_id:
            row = self.home.db.execute(
                'SELECT id FROM links WHERE package_id = ? AND environment_id = ?',
                [self.id_or_persist(), env.id_or_persist()]
            ).fetchone()
        if self.link_id or row:
            raise AlreadyLinked(str(frozen or self.freeze()), self.link_id or row[0])

    def persist_in_db(self):
        self._set_names(package=True, build=True, install=True)
        if not self.installed:
            log.warning('%s does not appear to be installed to %s' % (self.name, self.install_path))
            raise ValueError('cannot record requirement that is not installed')
        return super(Package, self).persist_in_db()

    def resolve_existing(self, env=None):
        """Check against the database to see if this was already installed."""

        if self.id is not None:
            raise ValueError('requirement already in database')


        clauses = ['install_path IS NOT NULL', 'url = ?']
        values  = [self.url]

        for name in ('name', 'revision', 'etag', 'package_name', 'build_name', 'install_name'):
            if getattr(self, name):
                clauses.append('%s = ?' % name)
                values.append(getattr(self, name))

        cur = self.home.db.cursor()
        clause = ' AND '.join(clauses)

        # print clause, values
        
        if env:
            values.append(env.id_or_persist())
            cur.execute('''
                SELECT packages.*, links.id as link_id FROM packages
                LEFT OUTER JOIN links ON packages.id = links.package_id
                WHERE %s AND links.environment_id = ?
                ORDER BY links.created_at DESC, packages.created_at DESC
            ''' % clause, values)
        else:
            cur.execute('''
                SELECT packages.*, NULL as link_id FROM packages
                WHERE %s
                ORDER BY packages.created_at DESC
            ''' % clause, values)

        for row in cur:
            if not os.path.exists(row['install_path']):
                log.warning('Found %s (%d) does not exist at %s' % (self.name or row['name'], row['id'], row['install_path']))
                continue
            break
        else:
            return

        log.debug('Found %s (%d) at %s' % (self.name or row['name'], row['id'], row['install_path']))

        self.restore_from_row(row, ignore=set(('abstract_requirements', 'concrete_requirement',
            'package_path', 'build_path', 'install_path')))
        self.link_id = row['link_id']

        # TODO: Do these warnings still make sense?
        if self.package_path != row['package_path']:
            pass # log.warning('Package paths don\'t match:\n  old: %r\n  new: %r' % (row['package_path'], self.package_path))
        if self.build_path != row['build_path']:
            pass # log.warning('Builds paths don\'t match:\n  old: %r\n  new: %r' % (row['build_path'], self.build_path))
        if self.install_path != row['install_path']:
            pass # log.warning('Install paths don\'t match:\n  old: %r\n  new: %r' % (row['install_path'], self.install_path))

        for name in 'package_path', 'build_path', 'install_path':
            setattr(self, name, row[name])

        return True

    def _record_link(self, env):
        cur = self.home.db.cursor()
        cur.execute('''INSERT INTO links (package_id, environment_id, abstract_requirement) VALUES (?, ?, ?)''', [
            self.id_or_persist(),
            env.id_or_persist(),
            self.abstract_requirement,
        ])
        self.link_id = cur.lastrowid


    def _reinstall_check(self, force):
        if self.installed:
            if force:
                self.uninstall()
            else:
                raise AlreadyInstalled(str(self.freeze()))


