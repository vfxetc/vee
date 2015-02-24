import datetime
import fnmatch
import glob
import os
import pkg_resources
import re
import shlex
import shutil

from vee.exceptions import AlreadyInstalled
from vee.utils import cached_property, style, call, call_log, makedirs
from vee.requirement import Requirement


def _find_in_tree(root, name, type='file'):
    pattern = fnmatch.translate(name)
    for dir_path, dir_names, file_names in os.walk(root):
        # Look for the file/directory.
        candidates = dict(file=file_names, dir=dir_names)[type]
        found = next((x for x in candidates if re.match(pattern, x)), None)
        if found:
            return os.path.join(dir_path, found)
        # Bail when we hit a fork in the directory tree.
        if len(dir_names) > 1 or file_names:
            return


class BasePackage(object):

    """Abstraction of a package manager.

    Packages are instances for each :class:`Requirement`, such that they are
    able to maintain state about that specific requirement.

    """

    type = 'base'

    # Pairs of Package vs Requirement attributes.
    _pkg_to_req_attrs = {
        '_base_name': 'name',
        '_force_fetch': 'force_fetch',
        '_install_name': 'install_name',
        '_install_subdir_from_build': 'install_prefix',
        '_build_subdir_to_install': 'build_subdir',
    }

    _req_to_pkg_attrs = dict((v, k) for k, v in _pkg_to_req_attrs.iteritems())


    def __init__(self, requirement=None, home=None):

        self.abstract_requirement = requirement and requirement.to_json()
        self.home = home or requirement.home

        for action in Requirement._arg_parser._actions:
            req_attr = action.dest
            pkg_attr = self._req_to_pkg_attrs.get(req_attr, req_attr)
            setattr(self, pkg_attr, requirement and getattr(requirement, req_attr))

        # A few need special handling
        self.environ = self.environ.copy() if self.environ else {}
        self.config = self.config[:] if self.config else []

        self._db_id = None
        self._package_name = self._build_name = None


    def __repr__(self):
        return '<%s for %s>' % (
            self.__class__.__name__,
            self.abstract_requirement,
        )

    def freeze(self):
        kwargs = {}
        for action in Requirement._arg_parser._actions:
            req_attr = action.dest
            pkg_attr = self._req_to_pkg_attrs.get(req_attr, req_attr)
            kwargs[req_attr] = getattr(self, pkg_attr)
        kwargs['environ'] = self.environ_diff
        return Requirement(home=self.home, **kwargs)

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
                print style('setenv', 'blue', bold=True), style('%s=' % k, bold=True) + v
        return self._environ_diff or {}

    def fresh_environ(self):
        environ = os.environ.copy()
        environ.update(self.environ_diff)
        return environ

    def _set_default_names(self, package=False, build=False, install=False):
        if (package or build or install) and self._package_name is None:
            self._package_name = self.url and os.path.join(self.type, re.sub(r'^https?://', '', self.url).strip('/'))
        if (install or build) and self._install_name is None:
            if self._base_name and self.revision:
                self._install_name = '%s/%s' % (self._base_name, self.revision)
            else:
                self._install_name = self._package_name and re.sub(r'(\.(tar|gz|tgz|zip))+$', '', self._package_name)
        if build and self._build_name is None:
            self._build_name = self._install_name and ('%s/%s-%s' % (
                self._install_name,
                datetime.datetime.utcnow().strftime('%y%m%d%H%M%S'),
                os.urandom(4).encode('hex'),
            ))

    def _set_names(self, **kwargs):
        self._set_default_names(**kwargs)

    def _assert_names(self, **kwargs):
        self._set_names(**kwargs)
        for attr, value in kwargs.iteritems():
            if value and not getattr(self, '_%s_name' % attr):
                raise RuntimeError('%s name required' % attr)

    def _assert_paths(self, **kwargs):
        self._set_names(**kwargs)
        for attr, value in kwargs.iteritems():
            if value and not getattr(self, '%s_path' % attr):
                raise RuntimeError('%s path required' % attr)

    @property
    def package_path(self):
        """Where the package is cached."""
        return self._package_name and self.home.abspath('packages', self._package_name)

    @property
    def build_path(self):
        """Where the package will be built."""
        return self._build_name and self.home.abspath('builds', self._build_name)

    @property
    def install_path(self):
        """The final location of the built package."""
        return self._install_name and self.home.abspath('installs', self._install_name)

    def fetch(self):
        """Cache package from remote source; return something representing the package."""

    @property
    def build_path_to_install(self):
        return os.path.join(self.build_path, self._build_subdir_to_install or '').rstrip('/')

    @property
    def install_path_from_build(self):
        return os.path.join(self.install_path, self._install_subdir_from_build or '').rstrip('/')

    def _clean_build_path(self, makedirs=True):
        if self.build_path and os.path.exists(self.build_path):
            shutil.rmtree(self.build_path)
        if makedirs:
            os.makedirs(self.build_path)

    def extract(self):
        """Extract the package into the (cleaned) build directory."""

        self._set_names(package=True, build=True)

        if not self.package_path:
            return
        if not self.build_path:
            raise RuntimeError('need build path for default Package.extract')

        print style('Extracting to', 'blue', bold=True), style(self.build_path, bold=True)

        # Tarballs.
        if re.search(r'(\.tgz|\.tar\.gz)$', self.package_path):
            self._clean_build_path()
            call(['tar', 'xzf', self.package_path], cwd=self.build_path)

        # Zip files.
        elif self.package_path.endswith('.zip'):
            self._clean_build_path()
            call(['unzip', self.package_path], cwd=self.build_path)

        # Directories.
        elif os.path.isdir(self.package_path):
            self._clean_build_path(makedirs=False)
            shutil.copytree(self.package_path, self.build_path, symlinks=True,
                ignore=shutil.ignore_patterns('.git'),
            )

        else:
            raise ValueError('unknown package type %r' % self.package_path)

    def build(self):
        """Build the package in the build directory."""

        env = None
        self._assert_paths(build=True)

        build_sh = _find_in_tree(self.build_path, 'vee-build.sh')
        if build_sh:

            print style('Running vee-build.sh...', 'blue', bold=True)
            env = env or self.fresh_environ()
            env.update(
                VEE=self.home.root,
                VEE_BUILD_PATH=self.build_path,
                VEE_INSTALL_NAME=self._install_name,
                VEE_INSTALL_PATH=self.install_path,
            )

            cwd = os.path.dirname(build_sh)
            envfile = os.path.join(cwd, 'vee-env-' + os.urandom(8).encode('hex'))
            call_log(['bash', '-c', '. vee-build.sh; env | grep VEE > %s' % (envfile)], env=env, cwd=cwd)

            env = list(open(envfile))
            env = dict(line.strip().split('=', 1) for line in env)
            os.unlink(envfile)

            self._build_subdir_to_install = env.get('VEE_BUILD_SUBDIR_TO_INSTALL') or ''
            self._install_subdir_from_build = env.get('VEE_INSTALL_SUBDIR_FROM_BUILD') or ''
            return

        setup_py = _find_in_tree(self.build_path, 'setup.py')
        if setup_py:

            top_level = os.path.dirname(setup_py)
            self._build_subdir_to_install = os.path.join(top_level, 'dist/vee')

            # Setup the PYTHONPATH to point to the "install" directory.
            env = env or self.fresh_environ()
            env['PYTHONPATH'] = '%s:%s' % ('dist/vee/lib/python2.7/site-packages', env.get('PYTHONPATH', ''))
            os.makedirs(os.path.join(top_level, 'dist/vee/lib/python2.7/site-packages'))

            print style('Building Python package...', 'blue', bold=True)

            # Need to inject setuptools for this.
            cmd = ['python', '-c', 'import setuptools; __file__="setup.py"; execfile(__file__)']
            cmd.extend(['build'])
            cmd.extend(self.config)
            cmd.extend(['install',
                '--root', '.',
                '--prefix', 'dist/vee',
                '--no-compile',
                '--single-version-externally-managed',
            ])

            if call(cmd, cwd=top_level, env=env):
                raise RuntimeError('Could not build Python package')
            return

        egg_info = _find_in_tree(self.build_path, '*.egg-info', 'dir')
        if egg_info:
            print style('Found Python egg:', 'blue', bold=True), style(os.path.basename(egg_info), bold=True)
            self._build_subdir_to_install = os.path.dirname(egg_info)
            # TODO: Get the right Python version.
            self._install_subdir_from_build = 'lib/python2.7/site-packages'
            return

        configure = _find_in_tree(self.build_path, 'configure')
        if configure:
            self._build_subdir_to_install = os.path.dirname(configure)
            print style('Configuring...', 'blue', bold=True)
            cmd = ['./configure', '--prefix', self.install_path]
            env = env or self.fresh_environ()
            cmd.extend(self.config)
            call(cmd, cwd=os.path.dirname(configure), env=env)

        makefile = _find_in_tree(self.build_path, 'Makefile')
        if makefile:
            self._build_subdir_to_install = os.path.dirname(makefile)
            print style('Making...', 'blue', bold=True)
            env = env or self.fresh_environ()
            call(['make', '-j4'], cwd=os.path.dirname(makefile), env=env)

    @property
    def installed(self):
        self._set_names(install=True)
        return self.install_path and os.path.exists(self.install_path)

    def install(self):
        """Install the build artifact into a final location."""

        self._set_names(build=True, install=True)
        if not self.build_path or not self.build_path_to_install:
            raise RuntimeError('need build path for default Package.install')
        if not self.install_path or not self.install_path_from_build:
            raise RuntimeError('need install path for default Package.install')

        # We are not using our wrapper, as we want this to fail if it is
        # already installed.
        if self.installed:
            raise AlreadyInstalled('was already installed at %s' % self.install_path)
        
        print style('Installing to', 'blue', bold=True), style(self.install_path, bold=True)

        shutil.copytree(self.build_path_to_install, self.install_path_from_build, symlinks=True)

        # Link into $VEE/opt.
        if self._base_name:
            opt_link = self.home.abspath('opt', self._base_name)
            print style('Linking to', 'blue', bold=True), style(opt_link, bold=True)
            if os.path.exists(opt_link):
                os.unlink(opt_link)
            makedirs(os.path.dirname(opt_link))
            os.symlink(self.install_path, opt_link)

    def uninstall(self):
        self._set_names(install=True)
        if not self.installed:
            raise RuntimeError('package is not installed')
        print style('Uninstalling', 'blue', bold=True), style(self.install_path, bold=True)
        shutil.rmtree(self.install_path)

    def link(self, env):
        self._assert_paths(install=True)
        env.link_directory(self.install_path)
        self._record_link(env)

    def db_id(self):
        if self._db_id is None:
            self._set_names(package=True, build=True, install=True)
            if not self.installed:
                raise ValueError('cannot record requirement that is not installed')
            cur = self.home.db.cursor()
            cur.execute('''
                INSERT INTO packages (created_at, abstract_requirement, concrete_requirement,
                                      type, url, name, revision, package_name, build_name,
                                      install_name, package_path, build_path, install_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [datetime.datetime.utcnow(),
                  self.abstract_requirement,
                  self.freeze().to_json(),
                  self.type,
                  self.url,
                  self._base_name,
                  self.revision,
                  self._package_name,
                  self._build_name,
                  self._install_name,
                  self.package_path,
                  self.build_path,
                  self.install_path,
                 ]
            )
            self._db_id = cur.lastrowid
        return self._db_id


    def resolve_existing(self):
        """Check against the database to see if this was already installed."""

        if self._db_id is not None:
            raise ValueError('requirement already in database')

        cur = self.home.db.cursor()

        clauses = ['type = ?', 'url = ?']
        values = [self.type, self.url]
        for attr, column in (
            ('_base_name', 'name'),
            ('revision', 'revision'),
        ):
            if getattr(self, attr):
                clauses.append('%s = ?' % attr)
                values.append(getattr(self, attr))
        for attr in ('_package_name', '_build_name', '_install_name'):
            if getattr(self, attr):
                clauses.append('%s = ?' % attr.strip('_'))
                values.append(getattr(self, attr))

        row = cur.execute('''
            SELECT * FROM packages
            WHERE %s
            ORDER BY created_at DESC
            LIMIT 1
        ''' % ' AND '.join(clauses), values).fetchone()

        if not row:
            return

        print style('DEBUG: found existing install %d' % row['id'], faint=True)

        # Everything below either already matches or was unset.
        self._db_id = row['id']
        self._base_name = row['name']
        self.revision = row['revision']
        self._package_name = row['package_name']
        self._build_name = row['build_name']
        self._install_name = row['install_name']
        if (self.package_path != row['package_path'] or
            self.build_path != row['build_path'] or
            self.install_path != row['install_path']
        ):
            raise RuntimeError('recorded paths dont match')

        return True

    def _record_link(self, env):
        cur = self.home.db.cursor()
        cur.execute('''INSERT INTO links (package_id, environment_id, created_at, abstract_requirement) VALUES (?, ?, ?, ?)''', [
            self.db_id(),
            env.db_id(),
            datetime.datetime.utcnow(),
            self.abstract_requirement,
        ])

