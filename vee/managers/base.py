import datetime
import glob
import os
import pkg_resources
import re
import shutil

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
    def package_name(self):
        return self._package_name

    @property
    def _package_name(self):
        return self.requirement.package.strip('/')

    @property
    def package_path(self):
        """Where the package is cached."""
        return self.home.abspath('packages', self.name, self.package_name)

    def fetch(self):
        """Cache package from remote source; return something representing the package."""

    def discover_existing_installs(self):
        pass

    @property
    def build_name(self):
        return self._build_name

    @cached_property
    def _build_name(self):
        return '%s/%s-%s' % (
            self.install_name,
            datetime.datetime.utcnow().strftime('%y%m%d%H%M%S'),
            os.urandom(4).encode('hex'),
        )

    @property
    def build_path(self):
        """Where the package will be built."""
        if not self.package_path:
            raise RuntimeError('need package path for default Manager.build_path')
        return self.home.abspath('builds', self.name, self.build_name)

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

        print colour('Extracting to build directory...', 'blue', bright=True, reset=True)

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

        def find(name):
            base = os.path.join(self.build_path, name)
            if os.path.exists(base):
                return base
            pattern = os.path.join(self.build_path, '*', name)
            files = glob.glob(pattern)
            return files[0] if files else None

        setup_py = find('setup.py')
        if setup_py:

            top_level = os.path.dirname(setup_py)
            build = os.path.join('build', 'lib', 'python2.7', 'site-packages')
            self._build_path_to_install = os.path.join(top_level, 'build')

            print colour('Building Python package...', 'blue', bright=True, reset=True)
            if call(['python', 'setup.py', 'build',
                '--build-temp', 'tmp',
                '--build-purelib', build,
                '--build-platlib', build,
            ], cwd=top_level, silent=True):
                raise RuntimeError('Could not build Python package')

            # Install egg-info (for entry_points, mostly).
            # Need to inject setuptools for this
            print colour('Building egg-info...', 'blue', bright=True, reset=True)
            if call(['python', '-c', 'import setuptools; __file__="%s"; execfile(__file__)' % (setup_py, ),
                'install_egg_info', '-d', build,
            ], cwd=top_level, silent=True):
                raise RuntimeError('Could not build Python egg_info')

            return

        configure = find('configure')
        if configure:
            self._build_path_to_install = os.path.dirname(configure)
            print colour('Configuring...', 'blue', bright=True, reset=True)
            call(['./configure'], cwd=os.path.dirname(configure))

        makefile = find('Makefile')
        if makefile:
            self._build_path_to_install = os.path.dirname(makefile)
            print colour('Making...', 'blue', bright=True, reset=True)
            call(['make', '-j4'], cwd=os.path.dirname(makefile))
    
    @property
    def install_name(self):
        if self.requirement.install_name:
            return self.requirement.install_name
        if self.requirement.name and self.requirement.revision:
            return '%s/%s' % (self.requirement.name, self.requirement.revision)
        return self._install_name

    @property
    def _install_name(self):
        return re.sub(r'(\.(tar|gz|tgz|zip))+$', '', self.package_name)

    @property
    def install_path(self):
        """The final location of the built package."""
        return self.home.abspath('installs', self.name, self.install_name)

    @property
    def installed(self):
        return os.path.exists(self.install_path)

    def install(self):
        """Install the build artifact into a final location."""

        if not self.build_path_to_install:
            raise RuntimeError('need build path for default Manager.install')
        if not self.install_path:
            raise RuntimeError('need install path for default Manager.install')

        # We are not using our wrapper, as we want this to fail if it is
        # already installed.
        if os.path.exists(self.install_path):
            raise RuntimeError('was already installed at %s' % self.install_path)
        
        print colour('Installing', 'blue', bright=True), colour(self.build_path_to_install, 'black', reset=True)
        print colour('        to', 'blue', bright=True), colour(self.install_path, 'black', reset=True)

        shutil.copytree(self.build_path_to_install, self.install_path, symlinks=True)

