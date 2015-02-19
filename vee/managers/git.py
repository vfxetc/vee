import os
import subprocess

from vee.managers.base import BaseManager
from vee.utils import call, call_output, makedirs, style
from vee.git import GitRepo


class GitManager(BaseManager):

    name = 'git'

    def __init__(self, *args, **kwargs):
        super(GitManager, self).__init__(*args, **kwargs)
        self._assert_paths(package=True)
        self.repo = GitRepo(work_tree=self.package_path, remote_url=self.requirement and self.requirement.package)

    def _set_names(self, build=False, install=False, **kwargs):
        if (build or install) and not self._build_name:
            commit = self.repo.rev_parse(self.requirement.revision or 'HEAD')
            if commit:
                super(GitManager, self)._set_names(package=True)
                self._build_name = '%s-%s' % (self._package_name, commit[:8])
        if install and not self._install_name:
                self._install_name = self._build_name
        super(GitManager, self)._set_names(**kwargs)

    def fetch(self):
        self.repo.checkout(self.requirement.revision or 'HEAD', force=self.requirement.force_fetch)
        self.requirement.revision = self.repo.head
        
