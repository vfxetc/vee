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
        return self.requirement.package.strip('/')

    @property
    def package_path(self):
        """Where the package is cached."""
        return self.home.abspath('packages', self.name, self.package_name)

    def fetch(self):
        """Cache package from remote source; return something representing the package."""

    def discover_existing_installs(self):
        pass

    @cached_property
    def build_name(self):
        return '%s/%s-%s' % (
            self.install_name,
            datetime.datetime.utcnow().isoformat('T'),
            os.urandom(4).encode('hex'),
        )

    @property
    def build_path(self):
        """Where the package will be built."""
        if not self.package_path:
            raise RuntimeError('need package path for default Manager.build_path')
        return self.home.abspath('builds', self.name, self.build_name)

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

        print colour('Extracting', 'blue', bright=True, reset=True)

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
            print "TODO: python setup.py"
            return

        configure = find('configure')
        if configure:
            print 'TODO: ./configure'

        makefile = find('Makefile')
        if makefile:
            print 'TODO: make'
    
    @property
    def install_name(self):
        return re.sub(r'(\.(tar|gz|tgz|zip))+$', '', self.package_name)

    @property
    def install_path(self):
        """The final location of the built package."""
        return self.home.abspath('installs', self.name, self.install_name)

    def install(self):
        """Install the build artifact into a final location."""

        if not self.build_path:
            raise RuntimeError('need build path for default Manager.install')
        if not self.install_path:
            raise RuntimeError('need install path for default Manager.install')

        # We are not using our wrapper, as we want this to fail if it is
        # already installed.
        if os.path.exists(self.install_path):
            raise RuntimeError('was already installed at %s' % self.install_path)
        
        shutil.copytree(self.build_path, self.install_path, symlinks=True)

