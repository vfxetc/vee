from copy import deepcopy
import argparse
import base64
import datetime
import fnmatch
import glob
import json
import os
import re
import shlex
import shutil
import sys

import six

import pkg_resources

from vee import libs
from vee import log
from vee.cli import style, style_note
from vee.database import DBObject, Column
from vee.exceptions import AlreadyInstalled, AlreadyLinked, CliMixin
from vee.pipeline.base import Pipeline
from vee.subproc import call
from vee.utils import cached_property, makedirs, linktree, guess_name
from vee.semver import Version, VersionExpr

from vee.package.provides import Provision
from vee.package.requires import RequirementSet


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
            for i in range(1, len(parts), 2):
                res[parts[i]] = parts[i + 1]


class _ProvidesAction(argparse.Action):

    @property
    def default(self):
        return Provision()

    @default.setter
    def default(self, v):
        pass

    def __call__(self, requirement_parser, namespace, values, option_string=None):
        res = getattr(namespace, self.dest)
        for value in values:
            res.parse(value)


class _RequiresAction(argparse.Action):

    @property
    def default(self):
        return RequirementSet()

    @default.setter
    def default(self, v):
        pass

    def __call__(self, requirement_parser, namespace, values, option_string=None):
        res = getattr(namespace, self.dest)
        for value in values:
            res.parse(value)

    


requirement_parser = _RequirementParser(add_help=False)

requirement_parser.add_argument('-n', '--name')
requirement_parser.add_argument('-r', '--revision')

requirement_parser.add_argument('-P', '--provides', nargs='*', action=_ProvidesAction)
requirement_parser.add_argument('-R', '--requires', nargs='*', action=_RequiresAction)
requirement_parser.add_argument('-V', '--variant',  nargs='*', dest='variants', action='append', default=[]) # TODO: Parse.

requirement_parser.add_argument('--etag', help='identifier for busting caches')
requirement_parser.add_argument('--checksum', help='to verify that package archives haven\'t changed')

requirement_parser.add_argument('--base-environ', nargs='*', action=_EnvironmentAction, help=argparse.SUPPRESS)
requirement_parser.add_argument('-e', '--environ', nargs='*', action=_EnvironmentAction, help='envvars for building')
requirement_parser.add_argument('-c', '--config', nargs='*', action=_ConfigAction, help='args to pass to `./configure`, `python setup.py`, `brew install`, etc..')

requirement_parser.add_argument('--autoconf', action='store_true', help='the package uses autoconf; may ./bootstrap')
requirement_parser.add_argument('--make-install', action='store_true', help='do `make install`')

requirement_parser.add_argument('--install-name')
requirement_parser.add_argument('--build-subdir')
requirement_parser.add_argument('--install-prefix')

requirement_parser.add_argument('--defer-setup-build', action='store_true', help='For Python packages, dont `python setup.py build` first')
requirement_parser.add_argument('--hard-link', action='store_true', help='use hard links instead of copies')
requirement_parser.add_argument('--pseudo-homebrew', action='store_true', help='assume is repackage of Homebrew')
requirement_parser.add_argument('--relocate', help='how to relocate shared libs on OS X, or RPATHS to set on Linux')
requirement_parser.add_argument('--set-rpath', help='what rpaths to set on Linux')
requirement_parser.add_argument('--virtual', action='store_true', help='package is runtime only; does not persist')

requirement_parser.add_argument('--develop-sh', help='shell script in repository to source to develop the package')
requirement_parser.add_argument('--build-sh', help='shell script in repository to source to build the package')
requirement_parser.add_argument('--install-sh', help='shell script in repository to source to install the package')
requirement_parser.add_argument('--manifest-txt', help='manifest to require for this package')

requirement_parser.add_argument('url')


def _json_default(x):
    func = getattr(x, '__json__', None)
    if func:
        return func()
    raise TypeError('Object of type {} is not JSON serializable'.format(type(x).__name__))


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

    def __init__(self, args=None, *, home=None, set=None, dev=False, parent=None, **kwargs):

        super(Package, self).__init__()

        self.home = home # Must be early due to some properties using this.

        if args and kwargs:
            raise ValueError('specify either args OR kwargs')

        if isinstance(args, self.__class__):
            kwargs = args.to_kwargs()
            args = None
        elif isinstance(args, dict):
            kwargs = args
            args = None

        if args:

            if isinstance(args, six.string_types):
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
                raise TypeError("args must be one of (str, list, tuple, dict); got {}".format(args.__class__))

        else:
            for action in requirement_parser._actions:
                name = action.dest
                setattr(self, name, kwargs.pop(name, action.default))
            if kwargs:
                raise ValueError("too many kwargs: {}".format(list(kwargs)))

        assert self.url
        
        # Assert we have a name.
        if self.name:
            if self.name.lower() != self.name:
                log.warning("package name {!r} was not lowercase".format(self.name))
                self.name = self.name.lower()
        else:
            self.name = guess_name(self.url)

        # Manual args.
        self.abstract_requirement = self.to_json()
        self.dependencies = []
        self.parent = parent
        self.set = set

        # Coercions. TODO in the parser
        self.provides = Provision.coerce(self.provides)
        self.requires = RequirementSet.coerce(self.requires)

        # Make sure to make copies of anything that is mutable.
        self.base_environ = self.base_environ.copy() if self.base_environ else {}
        self.environ = self.environ.copy() if self.environ else {}
        self.config = self.config[:] if self.config else []

        # Initialize other state not covered by the argument parser.
        self.link_id = None
        self.package_name = self.build_name = None
        self.package_path = self.build_path = self.install_path = None
        self.meta = None

        self._init_pipeline(dev=dev)

    def _init_pipeline(self, dev=False):

        # Create the pipeline object.
        if dev:
            self.package_name = self.build_name = self.url
            self.package_path = self.build_path = self.url
            self.pipeline = Pipeline(self, ['init', 'inspect', 'develop'])
        else:
            self.pipeline = Pipeline(self, [
                'init', 'fetch', 'extract', 'inspect', 'build', 'install',
                'post_install', 'relocate', 'optlink',
            ])

        # Give the fetch pipeline step a chance to normalize the name/URL.
        self.pipeline.run_to('init')

    def to_kwargs(self, copy=True):
        kwargs = {}
        for action in requirement_parser._actions:
            name = action.dest
            value = getattr(self, name)
            if value != action.default: # This is easily wrong.
                kwargs[name] = deepcopy(value) if copy else value
        return kwargs

    def to_json(self):
        return json.dumps(self.to_kwargs(copy=False), sort_keys=True, default=_json_default)

    def to_args(self, exclude=set()):

        argsets = []
        for action in requirement_parser._actions:

            name = action.dest
            if name in ('url', ) or name in exclude:
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
                value = ','.join('%s=%s' % (k, v) for k, v in sorted(value.items()))
            elif isinstance(value, (list, tuple)):
                value = ','.join(value)
            else:
                value = str(value)

            # Shell escape!
            if re.search(r'\s', value):
                value = "'%s'" % value.replace("'", "''")

            argsets.append(['%s=%s' % (option_str, str(value))])

        args = [self.url]
        for argset in sorted(argsets):
            args.extend(argset)
        return args

    def __str__(self):
        return ' '.join(self.to_args(exclude=('base_environ', )))

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def copy(self):
        return self.__class__(self.to_kwargs(copy=True), home=self.home, parent=self)

    def freeze(self, environ=True):
        kwargs = self.to_kwargs()
        if environ:
            kwargs['environ'] = self.environ_diff
        return self.__class__(kwargs, home=self.home)

    def flat_variants(self):

        if not self.variants:
            return [self.copy()]

        out = []
        for raw in self.variants:
            var = self.copy()
            for key, value in raw:
                if key in ('provides', 'requires'):
                    getattr(var, key).update(value)
                else:
                    setattr(var, key, value)
            out.append(var)
        return out

    def add_dependency(self, **kwargs):
        # TODO: Remove these once the solver is used.
        kwargs.setdefault('base_environ', self.base_environ)
        kwargs.setdefault('environ', self.environ)
        kwargs.setdefault('home', self.home)
        dep = Package(**kwargs)
        self.dependencies.append(dep)
        return dep

    def render_template(self, template, environ=None, name=None):

        environ = (environ or os.environ).copy()
        environ['VEE'] = self.home.root

        return re.sub(r'''
            \$\{(\w+)\}| # variables with braces:    ${XXX}
            \$  (\w+)  | # variables without braces: $XXX
             %  (\w+)% | # Windows variables:        %XXX%
            \$\((.+?)\)| # Makefile-like functions:  $(prefix XXX)
            (@)          # Token representing original value.
        ''', lambda m: self._render_template_match(environ, name, m), template, flags=re.VERBOSE)

    def _render_template_match(self, environ, old_name, m):

        name_a, name_b, name_c, func, orig = m.groups()

        name = name_a or name_b or name_c
        if name:
            return environ.get(name, '')

        if func:
            args = func.split()
            if args[0] in ('prefix', 'install_path'):
                if len(args) != 2:
                    raise ValueError('prefix function takes one argument')
                name = args[1]
                try:
                    pkg = self.set[name]
                except KeyError:
                    raise ValueError('unknown package %s' % name)
                if not pkg.install_path:
                    raise ValueError('%s does not have a set install_path' % name)
                return pkg.install_path
            else:
                raise ValueError('unknown environment function %r' % args[0])

        if orig and old_name:
            return environ.get(old_name)

    _environ_diff = None

    @property
    def environ_diff(self):
        if self._environ_diff is None:

            self._environ_diff = {}
            for e in (self.base_environ, self.environ):
                for k, v in e.items():
                    self._environ_diff[k] = self.render_template(v, name=k)

            # Just for debugging...
            for k, v in sorted(self._environ_diff.items()):
                old_v = os.environ.get(k)
                if old_v is not None:
                    v = v.replace(old_v, '@')
                v = v.replace(self.home.root, '$VEE')
                log.debug('%s %s=%s' % (
                    style('setenv', 'blue'), k, v
                ), verbosity=2)

        return self._environ_diff

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
                base64.b16encode(os.urandom(4)).decode(),
            ))

    def _assert_names(self, **kwargs):
        self._set_names(**kwargs)
        for attr, value in kwargs.items():
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
        for attr, value in kwargs.items():
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
        return bool(
            self.install_path and # The path is set,
            os.path.isdir(self.install_path) and # it exists as a directory,
            os.listdir(self.install_path) # and it has contents.
        )

    def uninstall(self):
        if not self.installed:
            raise RuntimeError('package is not installed')
        log.info(style_note('Uninstalling ', self.install_path))
        shutil.rmtree(self.install_path)

    def shared_libraries(self, rescan=False):
        if self.virtual:
            raise RuntimeError('cannot find libraries of virtual package')
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

    def persist_in_db(self, con=None):
        if self.virtual:
            raise RuntimeError('cannot persist virtual package')
        self._set_names(package=True, build=True, install=True)
        if not self.installed:
            log.warning('%s does not appear to be installed to %s' % (self.name, self.install_path))
            raise ValueError('cannot record requirement that is not installed')
        con = con or self.home.db.connect()
        with con:
            exists = self.id is not None
            res = super(Package, self).persist_in_db(con=con)
            if exists:
                con.execute('DELETE FROM package_dependencies WHERE depender_id = ?', [self.id])
            for dep in self.dependencies:
                dep_id = dep.id_or_persist(con=con)
                log.debug('Recorded %s -> %s dependency as %d' % (
                    self.name, dep.name, dep_id
                ))
                con.execute('INSERT INTO package_dependencies (depender_id, dependee_id) VALUES (?, ?)', [
                    self.id, dep_id
                ])
            return res



    def resolve_existing(self, env=None, weak=False):
        """Check against the database to see if this was already installed."""

        if self.id is not None:
            raise ValueError('requirement already in database')

        cur = self.home.db.cursor()

        # Dependencies are deferred.
        deferred = self.url.startswith('deferred:')
        if deferred:
            deferred_id = int(self.url.split(':')[1])
            cur.execute('SELECT * from packages WHERE id = ?', [deferred_id])
        
        else:

            clauses = ['install_path IS NOT NULL']
            values = []
            if not weak and self.url:
                clauses.append('url = ?')
                values.append(self.url)
            for name in ('name', 'etag', 'install_name'):
                if getattr(self, name):
                    clauses.append('%s = ?' % name)
                    values.append(getattr(self, name))
            clause = ' AND '.join(clauses)

            # log.debug('SELECT FROM packages WHERE %s' % ' AND '.join('%s = %r' % (c.replace(' = ?', ''), v) for c, v in zip(clauses[1:], values)), verbosity=2)

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
                    SELECT * FROM packages
                    WHERE %s
                    ORDER BY packages.created_at DESC
                ''' % clause, values)

        rev_expr = VersionExpr(self.revision) if self.revision else None
        for row in cur:
            if rev_expr and row['revision'] and not rev_expr.eval(Version(row['revision'])):
                log.debug('Found %s (%d) whose revision %s does not satisfy %s' % (
                    self.name or row['name'],
                    row['id'],
                    row['revision'],
                    rev_expr,
                ), verbosity=2)
                continue
            if not os.path.exists(row['install_path']):
                log.warning('Found %s (%d) does not exist at %s' % (self.name or row['name'], row['id'], row['install_path']))
                continue
            break
        else:

            if deferred:
                raise ValueError('deferred package %d no longer exists; consider `vee gc`' % deferred_id)
            return

        log.debug('Found %s (%d%s%s) at %s' % (
            self.name or row['name'],
            row['id'],
            ' weakly' if weak else '',
            ' in env %d' % env.id if env else '',
            row['install_path'],
        ))

        self.restore_from_row(row, ignore=set(('abstract_requirements', 'concrete_requirement')))
        self.link_id = row.get('link_id')

        if deferred:
            self._init_pipeline()

        self._load_dependencies(cur)

        return True

    def _load_dependencies(self, cursor=None):

        if self.dependencies:
            raise ValueError('dependencies already loaded')

        cur = cursor or self.home.db.cursor()

        # Set up weak references to dependencies. 
        cur.execute('SELECT dependee_id from package_dependencies WHERE depender_id = ?', [self.id])
        for row in cur:
            self.dependencies.append(Package(
                url='deferred:%d' % row['dependee_id'],
                home=self.home,
            ))

    def _record_link(self, env):
        cur = self.home.db.cursor()
        cur.execute('''INSERT INTO links (package_id, environment_id, abstract_requirement) VALUES (?, ?, ?)''', [
            self.id_or_persist(),
            env.id_or_persist(),
            self.abstract_requirement,
        ])
        self.link_id = cur.lastrowid


    def assert_uninstalled(self, uninstall=False):
        if self.installed:
            if uninstall:
                self.uninstall()
            else:
                raise AlreadyInstalled(str(self.freeze()))


