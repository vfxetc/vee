import os
import subprocess

from vee.managers.base import BaseManager
from vee.utils import call, call_output, makedirs, colour
from vee.git import GitRepo


class GitManager(BaseManager):

    name = 'git'

    def __init__(self, *args, **kwargs):
        super(GitManager, self).__init__(*args, **kwargs)
        self.repo = GitRepo(work_tree=self.package_path, remote_url=self.requirement and self.requirement.package)

    def fetch(self):
        self.repo.checkout(self.requirement.revision or 'HEAD', force=self.requirement.force_fetch)

    @property
    def _derived_build_name(self):
        commit = self.repo.rev_parse(self.requirement.revision or 'HEAD')
        if not commit:
            return None
        return '%s-%s' % (self._package_name, commit[:8])

    @property
    def _derived_install_name(self):
        # Git packages should include the repo in their install_name, instead
        # of just the base package_name like the rest do.
        return self._build_name




