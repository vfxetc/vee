import os
import subprocess

from vee.utils import call, call_output, style


class GitRepo(object):

    _head = None

    def __init__(self, work_tree, remote_url=None):
        self.work_tree = work_tree
        self.git_dir = os.path.join(work_tree, '.git')
        self.remote_url = remote_url

    @property
    def exists(self):
        return os.path.exists(self.git_dir)

    def clone_if_not_exists(self, remote_url=None, shallow=True):
        self.remote_url = remote_url or self.remote_url
        if self.exists:
            return
        if not self.remote_url:
            raise ValueError('git repo %r does not exist; need remote url' % self.git_dir)
        if os.path.exists(self.work_tree):
            # TODO: we can deal with this
            raise ValueError('work tree %r exists without repo' % self.work_tree)
        elif shallow:
            print style('Cloning shallow', 'blue', bold=True), style(self.remote_url, bold=True)
            call(['git', 'clone', '--depth=1', self.remote_url, self.work_tree])
        else:
            print style('Cloning', 'blue', bold=True), style(self.remote_url, bold=True)
            call(['git', 'clone', self.remote_url, self.work_tree])

    def _call(self, *cmd, **kw):
        return call(('git', '--git-dir', self.git_dir, '--work-tree', self.work_tree) + cmd, **kw)

    def rev_parse(self, revision, fetch=None):

        force_fetch = bool(fetch)
        allow_fetch = fetch or fetch is None

        if allow_fetch:
            self.clone_if_not_exists(shallow=True)

        if not force_fetch:
            commit = self._rev_parse(revision)

        if force_fetch or not commit:

            if not allow_fetch:
                raise ValueError('revision %r does not exist in local repo' % revision)

            if self.is_shallow:

                # Fetch the new history on top of the shallow history.
                print style('Fetching shallow', 'blue', bold=True), style(self.remote_url, bold=True)
                self._call('fetch', '--update-shallow', self.remote_url, silent=True)
                commit = self._rev_parse(revision)

                # Lets get the whole history.
                if not commit:
                    print style('Fetching unshallow', 'blue', bold=True), style(self.remote_url, bold=True)
                    self._call('fetch', '--unshallow', self.remote_url, silent=True)
                    commit = self._rev_parse(revision)

            else:
                # Normal fetch here.
                print style('Fetching', 'blue', bold=True), style(self.remote_url, bold=True)
                self._call('fetch', self.remote_url, silent=True)
                commit = self._rev_parse(revision)

        if not commit:
            msg = 'revision %r does not exist in %s' % (revision, self.remote_url)
            raise ValueError(msg)

        return commit

    def _rev_parse(self, revision):
        try:
            return self._call('rev-parse', '--verify', '--quiet', revision, stdout=True, silent=True).strip() or None
        except subprocess.CalledProcessError:
            pass

    def _current_head(self):
        self._head = self.rev_parse('HEAD')
        return self._head

    @property
    def head(self):
        return self._head or self._current_head()

    @property
    def is_shallow(self):
        return os.path.exists(os.path.join(self.git_dir, 'shallow'))

    def checkout(self, revision, fetch=None):
        commit = self.rev_parse(revision, fetch=fetch)
        if self.head != commit:
            print style('Checking out', 'blue', bold=True), style('%s [%s]' % (revision, commit), bold=True)
            self._call('reset', '--hard', commit, silent=True)
            self._head = commit




