import os

from vee.managers.git import GitManager
from vee.package import Package as BasePackage
from vee.utils import call, makedirs


class HomebrewManager(GitManager):

    name = 'homebrew'

    @property
    def _working_dir(self):
        return self.home.abspath('managers', self.name)

    @property
    def _remote_url(self):
        return 'https://github.com/Homebrew/homebrew.git'

    def _brew(self, *cmd):

        prefix = self._working_dir
        env = os.environ.copy()
        env.update(
            HOMEBREW=prefix,
            HOMEBREW_CELLAR=os.path.join(prefix, 'Cellar'),
            HOMEBREW_PREFIX=prefix,
            HOMEBREW_REPOSITORY=prefix,

            # These two are verified
            HOMEBREW_TEMP=makedirs(prefix, 'tmp'),
            HOMEBREW_CACHE=os.path.join(prefix, 'Cache'),
        )
        call((os.path.join(prefix, 'bin', 'brew'), ) + cmd, env=env)

    def install(self, package):
        self._brew('install', '--build-from-source', self.requirement.spec)

'''
class HomebrewPackage(BasePackage):
    pass


HomebrewManager.package_class = HomebrewPackage
'''