import json
import os
import shlex
import sys

from vee.managers.git import GitManager
from vee.utils import call, makedirs, colour


class HomebrewManager(GitManager):

    name = 'homebrew'

    def __init__(self, *args, **kwargs):
        super(HomebrewManager, self).__init__(*args, **kwargs)

    @property
    def _name_for_platform(self):
        return 'linuxbrew' if sys.platform.startswith('linux') else 'homebrew'

    @property
    def package_path(self):
        return self.home.abspath('packages', self._name_for_platform)

    @property
    def _git_remote_url(self):
        return 'https://github.com/Homebrew/%s.git' % self._name_for_platform

    @property
    def _brew_bin(self):
        return os.path.join(self.package_path, 'bin', 'brew')

    def _brew(self, *cmd, **kwargs):
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
        return call((self._brew_bin, ) + cmd, env=env, **kwargs)

    _cached_brew_info = None

    def _fresh_brew_info(self):
        if not os.path.exists(self._brew_bin):
            return {}
        self._cached_brew_info = json.loads(self._brew('info', '--json=v1', self.requirement.package, stdout=True, silent=True))[0]
        return self._cached_brew_info

    @property
    def _brew_info(self):
        if self._cached_brew_info is not None:
            return self._cached_brew_info
        else:
            return self._fresh_brew_info()

    def extract(self):
        # Disable BaseManager.extract().
        pass

    def build(self):
        if self.installed:
            print colour('Warning:', 'red', bright=True), colour(self.requirement + ' is already built', 'black', reset=True)
            return
        self._brew('install', self.requirement.package, *(
            shlex.split(self.requirement.configuration) if self.requirement.configuration else ()
        ))
        self._fresh_brew_info()

    @property
    def _build_name(self):
        return '%s/%s' % (
            self._brew_info['name'],
            self._brew_info['linked_keg'] or (
                self._brew_info['installed'][-1]['version']
                if self._brew_info['installed']
                else self._brew_info['versions']['stable']
            ),
        ) if self._brew_info else self._derived_build_name

    @property
    def build_path(self):
        return os.path.join(self.package_path, 'Cellar', self._install_name)

    _install_name = _build_name
    install_path = build_path

    def install(self):
        # Disable BaseManager.install().
        pass
