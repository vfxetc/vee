import os
import sys

from vee.managers.git import GitManager
from vee.utils import call, makedirs


class HomebrewManager(GitManager):

    name = 'homebrew'

    @property
    def _name_for_platform(self):
        return 'linuxbrew' if sys.platform.startswith('linux') else 'homebrew'

    @property
    def _git_work_tree(self):
        return self.home.abspath('managers', self._name_for_platform)

    @property
    def _git_remote_url(self):
        return 'https://github.com/Homebrew/%s.git' % self._name_for_platform

    def _brew(self, *cmd):

        prefix = self._git_work_tree
        env = os.environ.copy()
        env.update(
            # HOMEBREW=prefix,
            HOMEBREW_REPOSITORY=prefix,
            HOMEBREW_CACHE=os.path.join(prefix, 'Cache'),
            HOMEBREW_CELLAR=os.path.join(prefix, 'Cellar'),
            HOMEBREW_PREFIX=prefix,
            HOMEBREW_TEMP=makedirs(prefix, 'tmp'),
        )
        call((os.path.join(prefix, 'bin', 'brew'), ) + cmd, env=env)

    def install(self):
        self._brew('install', self.package.spec)