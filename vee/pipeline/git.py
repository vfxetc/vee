import os
import re
import subprocess

from vee.cli import style
from vee.git import GitRepo, normalize_git_url
from vee.pipeline.base import PipelineStep
from vee.subproc import call
from vee.utils import makedirs, cached_property


class GitTransport(PipelineStep):

    type = 'git'

    factory_priority = 1000

    @classmethod
    def factory(cls, step, pkg, *args):
        if step != 'fetch':
            return
        if re.match(r'^git[:+]', pkg.url):
            return cls(pkg, *args)

    def __init__(self, *args, **kwargs):

        self.repo = kwargs.pop('_repo', None)

        super(GitTransport, self).__init__(*args, **kwargs)
        pkg = self.package

        if not self.repo:
            # Normalize the URL if a repo wasn't handed to us.
            pkg.url = normalize_git_url(pkg.url, prefix=True) or pkg.url
            pkg._assert_paths(package=True)
            self.repo = GitRepo(work_tree=pkg.package_path, remote_url=re.sub(r'^git\+', '', pkg.url))
        

    def fetch(self):
        pkg = self.package
        self.repo.clone_if_not_exists()
        self.repo.checkout(pkg.revision or 'HEAD')
        pkg.revision = self.repo.head[:8]
