import os
import re
import subprocess

from vee.cli import style
from vee.git import GitRepo, normalize_git_url
from vee.packages.base import BasePackage
from vee.subproc import call
from vee.utils import makedirs, cached_property


class GitPackage(BasePackage):

    type = 'git'

    factory_priority = 1000

    @classmethod
    def factory(cls, req, *args):
        if re.match(r'^git[:+]', req.url):
            return cls(req, *args)

    def __init__(self, *args, **kwargs):
        super(GitPackage, self).__init__(*args, **kwargs)
        
        # We need to allow this to fail because the homebrew URLs, and others,
        # will likely fail.
        self.url = normalize_git_url(self.url, prefix=True) or self.url

        self._assert_paths(package=True)
        self.repo = GitRepo(work_tree=self.package_path, remote_url=self._git_remote_url)

    @cached_property
    def _git_remote_url(self):
        return re.sub(r'^git\+', '', self.url)
    
    def _set_names(self, build=False, install=False, **kwargs):
        if (build or install) and not self.build_name:
            self.repo.clone_if_not_exists()
            try:
                commit = self.repo.rev_parse(self.revision or 'HEAD', fetch=bool(self.revision))
            except ValueError:
                raise ValueError('%s does not exist in %s' % (self.revision or 'HEAD', self.repo.remote_url))
            if commit:
                if self.name:
                    self.build_name = '%s/%s' % (self.name, commit[:8])
                else:
                    super(GitPackage, self)._set_names(package=True)
                    self.build_name = '%s-%s' % (self.package_name, commit[:8])
        if install and not self.install_name:
                self.install_name = self.build_name
        super(GitPackage, self)._set_names(**kwargs)

    def fetch(self):
        self.repo.checkout(self.revision or 'HEAD')
        self.revision = self.repo.head[:8]
