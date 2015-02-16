import datetime
import fnmatch
import glob
import os
import pkg_resources
import re
import shlex
import shutil

from vee.exceptions import AlreadyInstalled
from vee.utils import cached_property, colour, call


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


class BaseManager(object):

    """Abstraction of a package manager.

    Managers are instances for each :class:`Requirement`, such that they are
    able to maintain state about that specific requirement.

    """

    name = 'base'

    def __init__(self, requirement=None, home=None):
        self.requirement = requirement
        self.home = home or requirement.home

    def __repr__(self):
        return '<%s for %s>' % (
            self.__class__.__name__,
            self.requirement,
        )

    _environ_diff = None

    @property
    def environ_diff(self):
        if self._environ_diff is None:
            self._environ_diff = self.requirement.resolve_environ()
            for k, v in sorted(self._environ_diff.iteritems()):
                print colour('setenv', 'blue', bright=True), colour('%s=' % k, 'black', reset=True) + v
        return self._environ_diff

    def fresh_environ(self):
        environ = os.environ.copy()
        environ.update(self.environ_diff)
        return environ

    @property
    def _package_name(self):
        return self._derived_package_name

    @property
    def _derived_package_name(self):
        return os.path.join(self.name, self.requirement.package.strip('/'))

    @property
    def package_path(self):
        """Where the package is cached."""
        return self.home.abspath('packages', self._package_name)

    def fetch(self):
        """Cache package from remote source; return something representing the package."""

    @property
    def _build_name(self):
        return self._derived_build_name

    @cached_property
    def _derived_build_name(self):
        return '%s/%s-%s' % (
            self._install_name,
            datetime.datetime.utcnow().strftime('%y%m%d%H%M%S'),
            os.urandom(4).encode('hex'),
        )

    @property
    def build_path(self):
        """Where the package will be built."""
        if not self.package_path:
            raise RuntimeError('need package path for default Manager.build_path')
        return self.home.abspath('builds', self.name, self._build_name)

    _build_subdir_to_install = None
    @property
    def build_path_to_install(self):
        return os.path.join(self.build_path, self._build_subdir_to_install or '').rstrip('/')

    _install_subdir_from_build = None
    @property
    def install_path_from_build(self):
        return os.path.join(self.install_path, self.requirement.install_subdir or self._install_subdir_from_build or '').rstrip('/')

    def _clean_build_path(self, makedirs=True):
        if self.build_path and os.path.exists(self.build_path):
            shutil.rmtree(self.build_path)
        if makedirs:
            os.makedirs(self.build_path)

    def extract(self):
        """Extract the package into the (cleaned) build directory."""

        if not self.package_path:
            return

        if not self.build_path:
            raise RuntimeError('need build path for default Manager.extract')

        print colour('Extracting to', 'blue', bright=True), colour(self.build_path, 'black', reset=True)

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

        build_sh = _find_in_tree(self.build_path, 'vee-build.sh')
        if build_sh:

            print colour('Running vee-build.sh...', 'blue', bright=True, reset=True)
            env = env or self.fresh_environ()
            env.update(
                VEE=self.home.root,
                VEE_BUILD_PATH=self.build_path,
                VEE_INSTALL_NAME=self._install_name,
                VEE_INSTALL_PATH=self.install_path,
            )

            cwd = os.path.dirname(build_sh)
            envfile = os.path.join(cwd, 'vee-env-' + os.urandom(8).encode('hex'))
            call(['bash', '-c', '. vee-build.sh; env | grep VEE > %s' % (envfile)], env=env, cwd=cwd)

            env = list(open(envfile))
            env = dict(line.strip().split('=', 1) for line in env)
            os.unlink(envfile)

            self._build_subdir_to_install = env.get('VEE_BUILD_SUBDIR_TO_INSTALL') or ''
            self._install_subdir_from_build = env.get('VEE_INSTALL_SUBDIR_FROM_BUILD') or ''
            return

        setup_py = _find_in_tree(self.build_path, 'setup.py')
        if setup_py:

            top_level = os.path.dirname(setup_py)
            # TODO: Get the right Python version.
            build = os.path.join('build', 'lib')
            self._build_subdir_to_install = os.path.join(top_level, build)
            self._install_subdir_from_build = 'lib/python2.7/site-packages'

            env = env or self.fresh_environ()

            print colour('Building Python package...', 'blue', bright=True, reset=True)
            cmd = [
                'python', 'setup.py', 'build',
                '--build-temp', 'tmp',
                '--build-purelib', build,
                '--build-platlib', build,
            ]
            if self.requirement.configuration:
                cmd.extend(shlex.split(self.requirement.configuration))
            if call(cmd, cwd=top_level, env=env):
                raise RuntimeError('Could not build Python package')

            # Install egg-info (for entry_points, mostly).
            # Need to inject setuptools for this
            print colour('Building egg-info...', 'blue', bright=True, reset=True)
            if call(['python', '-c', 'import setuptools; __file__="%s"; execfile(__file__)' % (setup_py, ),
                'install_egg_info', '-d', build,
            ], cwd=top_level, env=env):
                raise RuntimeError('Could not build Python egg_info')
            return

        egg_info = _find_in_tree(self.build_path, '*.egg-info', 'dir')
        if egg_info:
            print colour('Found Python egg:', 'blue', bright=True), colour(os.path.basename(egg_info), 'black', reset=True)
            self._build_subdir_to_install = os.path.dirname(egg_info)
            # TODO: Get the right Python version.
            self._install_subdir_from_build = 'lib/python2.7/site-packages'
            return

        configure = _find_in_tree(self.build_path, 'configure')
        if configure:
            self._build_subdir_to_install = os.path.dirname(configure)
            print colour('Configuring...', 'blue', bright=True, reset=True)
            cmd = ['./configure', '--prefix', self.install_path]
            env = env or self.fresh_environ()
            if self.requirement.configuration:
                cmd.extend(shlex.split(self.requirement.configuration))
            call(cmd, cwd=os.path.dirname(configure), env=env)

        makefile = _find_in_tree(self.build_path, 'Makefile')
        if makefile:
            self._build_subdir_to_install = os.path.dirname(makefile)
            print colour('Making...', 'blue', bright=True, reset=True)
            env = env or self.fresh_environ()
            call(['make', '-j4'], cwd=os.path.dirname(makefile), env=env)
    
    @property
    def _install_name(self):
        if self.requirement.install_name:
            return self.requirement.install_name
        if self.requirement.name and self.requirement.revision:
            return '%s/%s' % (self.requirement.name, self.requirement.revision)
        return self._derived_install_name

    @property
    def _derived_install_name(self):
        return re.sub(r'(\.(tar|gz|tgz|zip))+$', '', self._package_name)

    _install_subdir = None

    @property
    def install_path(self):
        """The final location of the built package."""
        return self._install_name and self.home.abspath('installs', self._install_name, self._install_subdir or '').rstrip('/')

    @property
    def installed(self):
        return self.install_path and os.path.exists(self.install_path)

    def install(self):
        """Install the build artifact into a final location."""

        if not self.build_path or not self.build_path_to_install:
            raise RuntimeError('need build path for default Manager.install')
        if not self.install_path or not self.install_path_from_build:
            raise RuntimeError('need install path for default Manager.install')

        # We are not using our wrapper, as we want this to fail if it is
        # already installed.
        if self.installed:
            raise AlreadyInstalled('was already installed at %s' % self.install_path)
        
        print colour('Installing to', 'blue', bright=True), colour(self.install_path, 'black', reset=True)

        shutil.copytree(self.build_path_to_install, self.install_path_from_build, symlinks=True)

    def uninstall(self):
        if not self.installed:
            raise RuntimeError('cannot uninstall package which is not installed')
        print colour('Uninstalling', 'blue', bright=True), colour(self.install_path, 'black', reset=True)
        shutil.rmtree(self.install_path)

    def link(self, env):
        env.link_directory(self.install_path)

