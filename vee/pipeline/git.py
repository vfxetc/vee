import os
import re
import subprocess

from vee.cli import style
from vee.git import GitRepo, normalize_git_url
from vee.pipeline.base import PipelineStep
from vee.subproc import call
from vee.utils import makedirs, cached_property


class GitTransport(PipelineStep):

    factory_priority = 1000

    @classmethod
    def factory(cls, step, pkg):
        if step == 'init' and re.match(r'^git[:+]', pkg.url):
            return cls()

    def get_next(self, step, pkg):
        if step == 'fetch':
            return self

    def init(self, pkg):
        
        pkg.url = normalize_git_url(pkg.url, prefix=True) or pkg.url
        pkg._assert_paths(package=True)
        self.repo = GitRepo(work_tree=pkg.package_path, remote_url=re.sub(r'^git[:\+]', '', pkg.url))
    
        # Resolve branches by fetching.
        if pkg.version and not re.match(r'^[0-9a-f]{8,}$', pkg.version):
            self.repo.clone_if_not_exists()
            rev = self.repo.fetch(ref=pkg.version)
            pkg.version = rev[:8]

    def fetch(self, pkg):
        self.repo.clone_if_not_exists()
        self.repo.checkout(pkg.version or 'HEAD', fetch=True)
        self.repo.git('submodule', 'update', '--init')
        pkg.version = self.repo.head[:8]
