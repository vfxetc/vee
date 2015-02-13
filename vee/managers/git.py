import os
import subprocess

from vee.managers.base import BaseManager
from vee.utils import call, call_output, makedirs, colour
from vee.git import GitRepo


class GitManager(BaseManager):

    name = 'git'

    def __init__(self, *args, **kwargs):
        super(GitManager, self).__init__(*args, **kwargs)
        self.repo = GitRepo(work_tree=self.package_path, remote_url=self.requirement.package)

    def fetch(self):
        self.repo.checkout(self.requirement.revision or 'HEAD')

    @property
    def _derived_build_name(self):
        # _build_name is pulled by _install_name below, which is used to detect
        # if the requirement is installed. This can happen before the repo is
        # cloned, so we need to come up with a dummy name.
        commit = self.repo.rev_parse(self.requirement.revision or 'HEAD') or 'notexist'
        return '%s-%s' % (self._package_name, commit[:8])

    @property
    def _derived_install_name(self):
        return self._build_name




