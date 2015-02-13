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

    @property
    def _package_name(self):
        return self._derived_package_name

    @property
    def _derived_package_name(self):
        return self.requirement.package.strip('/')

    @property
    def package_path(self):
        """Where the package is cached."""
        return self.home.abspath('packages', self.name, self._package_name)

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

    _build_path_to_install = None

    @property
    def build_path_to_install(self):
        return self._build_path_to_install or self.build_path

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

        def find(name, type='file'):
            pattern = fnmatch.translate(name)
            for dir_path, dir_names, file_names in os.walk(self.build_path):
                # Look for the file/directory.
                candidates = dict(file=file_names, dir=dir_names)[type]
                found = next((x for x in candidates if re.match(pattern, x)), None)
                if found:
                    return os.path.join(dir_path, found)
                # Bail when we hit a fork in the directory tree.
                if len(dir_names) > 1 or file_names:
                    return

        egg_info = find('*.egg-info', 'dir')
        if egg_info:
            print colour('Found Python egg:', 'blue', bright=True), colour(os.path.basename(egg_info), 'black', reset=True)
            self._build_path_to_install = os.path.dirname(egg_info)
            # TODO: Get the right Python version.
            self._install_subdir = 'lib/python2.7/site-packages'
            return

        setup_py = find('setup.py')
        if setup_py:

            top_level = os.path.dirname(setup_py)
            # TODO: Get the right Python version.
            build = os.path.join('build', 'lib', 'python2.7', 'site-packages')
            self._build_path_to_install = os.path.join(top_level, 'build')

            print colour('Building Python package...', 'blue', bright=True, reset=True)
            if call(['python', 'setup.py', 'build',
                '--build-temp', 'tmp',
                '--build-purelib', build,
                '--build-platlib', build,
            ], cwd=top_level):
                raise RuntimeError('Could not build Python package')

            # Install egg-info (for entry_points, mostly).
            # Need to inject setuptools for this
            print colour('Building egg-info...', 'blue', bright=True, reset=True)
            if call(['python', '-c', 'import setuptools; __file__="%s"; execfile(__file__)' % (setup_py, ),
                'install_egg_info', '-d', build,
            ], cwd=top_level):
                raise RuntimeError('Could not build Python egg_info')
            return

        configure = find('configure')
        if configure:
            self._build_path_to_install = os.path.dirname(configure)
            print colour('Configuring...', 'blue', bright=True, reset=True)
            cmd = ['./configure', '--prefix', self.install_path]
            if self.requirement.configuration:
                cmd.extend(shlex.split(self.requirement.configuration))
            call(cmd, cwd=os.path.dirname(configure))

        makefile = find('Makefile')
        if makefile:
            self._build_path_to_install = os.path.dirname(makefile)
            print colour('Making...', 'blue', bright=True, reset=True)
            call(['make', '-j4'], cwd=os.path.dirname(makefile))
    
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
        return self._install_name and self.home.abspath('installs', self.name, self._install_name, self._install_subdir or '').rstrip('/')

    @property
    def installed(self):
        return self.install_path and os.path.exists(self.install_path)

    def install(self):
        """Install the build artifact into a final location."""

        if not self.build_path_to_install:
            raise RuntimeError('need build path for default Manager.install')
        if not self.install_path:
            raise RuntimeError('need install path for default Manager.install')

        # We are not using our wrapper, as we want this to fail if it is
        # already installed.
        if self.installed:
            raise AlreadyInstalled('was already installed at %s' % self.install_path)
        
        print colour('Installing to', 'blue', bright=True), colour(self.install_path, 'black', reset=True)

        shutil.copytree(self.build_path_to_install, self.install_path, symlinks=True)

    def uninstall(self):
        if not self.installed:
            raise RuntimeError('cannot uninstall package which is not installed')
        print colour('Uninstalling', 'blue', bright=True), colour(self.install_path, 'black', reset=True)
        shutil.rmtree(self.install_path)

