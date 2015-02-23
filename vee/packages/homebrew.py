import json
import os
import shlex
import sys

from vee.packages.git import GitPackage
from vee.utils import call, makedirs, style


class HomebrewPackage(GitPackage):

    type = 'homebrew'

    @property
    def _name_for_platform(self):
        return 'linuxbrew' if sys.platform.startswith('linux') else 'homebrew'

    @property
    def _git_remote_url(self):
        return 'https://github.com/Homebrew/%s.git' % self._name_for_platform

    @property
    def _brew_bin(self):
        return os.path.join(self.package_path, 'bin', 'brew')

    def _brew(self, *cmd, **kwargs):
        
        self.repo.clone_if_not_exists()

        package = self.package_path
        env = os.environ.copy()
        env.update(
            # HOMEBREW=prefix,
            HOMEBREW_REPOSITORY=package,
            HOMEBREW_CACHE=os.path.join(package, 'Cache'),
            HOMEBREW_CELLAR=os.path.join(package, 'Cellar'),
            HOMEBREW_PREFIX=package,
            HOMEBREW_TEMP=makedirs(package, 'tmp'),
        )
        env.update(self.environ_diff)
        return call((self._brew_bin, ) + cmd, env=env, **kwargs)

    _cached_brew_info = None

    def _brew_info(self, name=None, force=False):

        if self._cached_brew_info is None:
            self._cached_brew_info = {}

        name = name or self.url
        if force or name not in self._cached_brew_info:
            self._cached_brew_info[name] = json.loads(self._brew('info', '--json=v1', name, stdout=True, silent=True))[0]

        return self._cached_brew_info[name]

    def _set_names(self, package=False, build=False, install=False):
        if package:
            self._package_name = self.url
        if build or install:
            self._build_name = self._install_name = self._install_name_from_info()

    def _install_name_from_info(self, name=None, info=None):
        name = name or self.url
        info = info or self._brew_info(name)
        if not info:
            raise ValueError('no homebrew package %s' % name)
        return '%s/%s' % (info['name'], info['linked_keg'] or (
            info['installed'][-1]['version']
            if info['installed']
            else info['versions']['stable']
        ))

    @property
    def package_path(self):
        return self.home.abspath('packages', self._name_for_platform)

    @property
    def build_path(self):
        return self._install_name and os.path.join(self.package_path, 'Cellar', self._install_name)

    install_path = build_path

    def extract(self):
        # Disable BasePackage.extract().
        pass

    def build(self):
        if self.installed:
            print style('Warning:', 'red', bold=True), style(self.url + ' is already built', 'black', bold=True)
            return
        self._brew('install', self.url, *self.config)

        # Need to force a new installed version number.
        self._brew_info(force=True)

    def install(self):
        # Disable BasePackage.install().
        pass

    def link(self, env):
        self._assert_paths(install=True)
        # We want to link in all dependencies as well.
        for name in self._brew('deps', '-n', self.url, silent=True, stdout=True).strip().split():
            path = os.path.join(self.package_path, 'Cellar', self._install_name_from_info(name))
            if os.path.exists(path):
                print style('Linking', 'blue', bold=True), style('homebrew+%s (homebrew+%s dependency)' % (name, self.url), bold=True)
                env.link_directory(path)
        env.link_directory(self.install_path)
