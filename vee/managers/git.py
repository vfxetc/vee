import os
import subprocess

from vee.managers.base import BaseManager
from vee.utils import call, call_output, makedirs, colour


class GitManager(BaseManager):

    name = 'git'

    @property
    def _git_dir(self):
        return os.path.join(self.package_path, '.git')

    @property
    def _git_remote_url(self):
        return self.requirement.package

    def _assert_checked_out(self, revision=None):

        if not os.path.exists(self._git_dir):
            makedirs(self.package_path)

            if revision:
                print colour('Cloning', 'blue', bright=True), colour(self._git_remote_url, 'black') + colour('', reset=True)
                call(['git', 'clone', self._git_remote_url, self.package_path])
            else:
                print colour('Cloning (shallow)', 'blue', bright=True), colour(self._git_remote_url, 'black') + colour('', reset=True)
                call(['git', 'clone', '--depth=1', self._git_remote_url, self.package_path])

        self._commit = head = self._git_rev_parse('HEAD')

        if revision:

            commit = self._git_rev_parse(revision)

            if not commit:

                print colour('Warning:', 'yellow', bright=True), colour('revision %r does not exist.' % revision, 'black', reset=True)

                if os.path.exists(os.path.join(self._git_dir, 'shallow')):
                    print colour('Fetching unshallow', 'blue', bright=True), colour(self._git_remote_url, 'black') + colour('', reset=True)
                    self._git('fetch', '--unshallow', self._git_remote_url)
                else:
                    print colour('Fetching', 'blue', bright=True), colour(self._git_remote_url, 'black') + colour('', reset=True)
                    self._git('fetch', self._git_remote_url)

                commit = self._git_rev_parse(revision)

            if not commit:
                msg = 'revision %r does not exist in %s' % (revision, self._git_remote_url)
                print colour('Error:', 'red'), colour(msg, reset=True)
                raise ValueError(msg)

            if head != commit:
                print colour('Checking out', 'blue', bright=True), colour('%s [%s]' % (revision, commit), 'black') + colour('', reset=True)
                self._git('reset', '--hard', commit, silent=True)

            self._commit = commit

    def _git(self, *cmd, **kw):
        return call(('git', '--git-dir', self._git_dir, '--work-tree', self.package_path) + cmd, **kw)

    def _git_rev_parse(self, revision):
        try:
            return self._git('rev-parse', '--verify', '--quiet', revision, stdout=True, silent=True).strip()
        except subprocess.CalledProcessError:
            pass


    def fetch(self):
        self._assert_checked_out(self.requirement.revision)

    @property
    def _build_name(self):
        return '%s-%s' % (self.package_name, self._commit[:8])

    @property
    def _install_name(self):
        return self.build_name




