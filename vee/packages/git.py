import os
import re
import subprocess

from vee.packages.base import BasePackage
from vee.utils import call, call_output, makedirs, style, cached_property
from vee.git import GitRepo


def normalize_git_url(url, prefix=True):

    if not isinstance(prefix, basestring):
        prefix = 'git+' if prefix else ''

    # Strip fragments.
    url = re.sub(r'#.*$', '', url)

    # The git protocol.
    m = re.match(r'^git:(//)?(.+)$', url)
    if m:
        return 'git://' + m.group(2)

    # Assert prefix on ssh and http urls. Note: this accepts at least all of
    # the schemes that git does.
    m = re.match(r'^(?:git\+)?(\w+):(.+)$', url)
    if m:
        scheme, the_rest = m.groups()
        return '%s%s:%s' % (prefix, scheme, the_rest)

    # Convert quick files into SSH.
    m = re.match(r'^git\+(/.+)$', url)
    if m:
        return '%sfile://%s' % (prefix, m.group(1))

    # Convert scp-like urls into SSH.
    m = re.match(r'^(?:git\+)?([^:@]+@)?([^:]+):/*(.*)$', url)
    if m:
        userinfo, host, path = m.groups()
        return '%sssh://%s%s/%s' % (prefix, userinfo or '', host, path.strip('/'))






class GitPackage(BasePackage):

    type = 'git'

    factory_priority = 1000

    @classmethod
    def factory(cls, req, home):
        if re.match(r'^git[:+]', req.url):
            return cls(req, home)

    def __init__(self, *args, **kwargs):
        super(GitPackage, self).__init__(*args, **kwargs)
        
        # We need to allow this to fail because the homebrew URLs, and others,
        # will likely fail.
        self.url = normalize_git_url(self.url) or self.url

        self._assert_paths(package=True)
        self.repo = GitRepo(work_tree=self.package_path, remote_url=self._git_remote_url)

    @cached_property
    def _git_remote_url(self):
        return re.sub(r'^git\+', '', self.url)
    
    def _set_names(self, build=False, install=False, **kwargs):
        if (build or install) and not self.build_name:
            self.repo.clone_if_not_exists()
            commit = self.repo.rev_parse(self.revision or 'HEAD')
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
        self.repo.checkout(self.revision or 'HEAD', fetch=self.force_fetch or None)
        self.revision = self.repo.head[:8]
