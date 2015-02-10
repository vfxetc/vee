import os

from vee.managers.base import BaseManager
from vee.utils import call, makedirs


class GitManager(BaseManager):

    name = 'git'

    @property
    def _working_dir(self):
        return self.home.abspath('managers', self.name, self.requirement.spec.strip('/'))

    @property
    def _local_repo(self):
        return os.path.join(self._working_dir, '.git')

    @property
    def _remote_url(self):
        return self.requirement.spec

    def _assert_checked_out(self):
        if not os.path.exists(self._local_repo):
            makedirs(self._working_dir)
            call(['git', 'clone', '--depth=1', self._remote_url, self._working_dir])

    def fetch(self, package):
        self._assert_checked_out()
