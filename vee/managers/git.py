import os
import subprocess

from vee.managers.base import BaseManager
from vee.utils import call, call_output, makedirs, colour


class GitManager(BaseManager):

    name = 'git'

    @property
    def _git_work_tree(self):
        return self.home.abspath('managers', self.name, self.package.spec.strip('/'))

    @property
    def _git_dir(self):
        return os.path.join(self._git_work_tree, '.git')

    @property
    def _git_remote_url(self):
        return self.package.spec

    def _assert_checked_out(self, revision=None):

        if not os.path.exists(self._git_dir):
            makedirs(self._git_work_tree)

            if revision:
                print colour('Cloning', 'blue', bright=True), colour(self._git_remote_url, 'black') + colour('', reset=True)
                call(['git', 'clone', self._git_remote_url, self._git_work_tree])
            else:
                print colour('Cloning (shallow)', 'blue', bright=True), colour(self._git_remote_url, 'black') + colour('', reset=True)
                call(['git', 'clone', '--depth=1', self._git_remote_url, self._git_work_tree])

        if revision:

            head = self._git_output('rev-parse', 'HEAD', silent=True)

            try:
                commit = self._git_output('rev-parse', '--verify', '--quiet', revision, silent=True)
            except subprocess.CalledProcessError:
                commit = None

            if not commit:

                print colour('Warning:', 'yellow', bright=True), colour('revision %r does not exist.' % revision, 'black', reset=True)

                if os.path.exists(os.path.join(self._git_dir, 'shallow')):
                    print colour('Fetching unshallow', 'blue', bright=True), colour(self._git_remote_url, 'black') + colour('', reset=True)
                    self._git('fetch', '--unshallow', self._git_remote_url)
                else:
                    print colour('Fetching', 'blue', bright=True), colour(self._git_remote_url, 'black') + colour('', reset=True)
                    self._git('fetch', self._git_remote_url)

            try:
                commit = self._git_output('rev-parse', '--verify', '--quiet', revision, silent=True)
            except subprocess.CalledProcessError:
                msg = 'rev %r does not exist in %s' % (revision, self._git_remote_url)
                print colour('Error:', 'red'), colour(msg, reset=True)
                raise ValueError(msg)

            if head != commit:
                print colour('Checking out', 'blue', bright=True), colour('%s [%s]' % (revision, commit), 'black') + colour('', reset=True)
                self._git('reset', '--hard', commit, silent=True)


    def _git(self, *cmd, **kw):
        call(('git', '--git-dir', self._git_dir, '--work-tree', self._git_work_tree) + cmd, **kw)

    def _git_output(self, *cmd, **kw):
        return call_output(('git', '--git-dir', self._git_dir, '--work-tree', self._git_work_tree) + cmd, **kw).strip()

    def fetch(self):
        self._assert_checked_out(self.package.revision)
        return self._git_work_tree


