import os
import subprocess

from vee.packages.base import BasePackage
from vee.utils import call, call_output, makedirs, style
from vee.git import GitRepo


class GitPackage(BasePackage):

    type = 'git'

    def __init__(self, *args, **kwargs):
        super(GitPackage, self).__init__(*args, **kwargs)
        self._assert_paths(package=True)
        self.repo = GitRepo(work_tree=self.package_path, remote_url=self._git_remote_url)

    @property
    def _git_remote_url(self):
        return self.url
    
    def _set_names(self, build=False, install=False, **kwargs):
        if (build or install) and not self._build_name:
            self.repo.clone_if_not_exists()
            commit = self.repo.rev_parse(self.revision or 'HEAD')
            if commit:
                if self.name:
                    self._build_name = '%s/%s' % (self.name, commit[:8])
                else:
                    super(GitPackage, self)._set_names(package=True)
                    self._build_name = '%s-%s' % (self._package_name, commit[:8])
        if install and not self._install_name:
                self._install_name = self._build_name
        super(GitPackage, self)._set_names(**kwargs)

    def fetch(self):
        self.repo.checkout(self.revision or 'HEAD', fetch=self._force_fetch or None)
        self.revision = self.repo.head[:8]
        
