import os
import re
import subprocess
from subprocess import CalledProcessError

from vee.utils import call, style


class GitRepo(object):

    _head = None

    def __init__(self, work_tree, remote_url=None, remote_name='origin', branch_name='master'):
        self.work_tree = work_tree
        self.git_dir = os.path.join(work_tree, '.git')
        self.remote_url = remote_url
        self.remote_name = remote_name
        self.branch_name = branch_name

    @property
    def exists(self):
        return os.path.exists(self.git_dir)

    def abspath(self, *args):
        return os.path.join(self.work_tree, *args)

    def clone_if_not_exists(self, remote_url=None, shallow=True):
        self.remote_url = remote_url or self.remote_url
        if self.exists:
            return
        if not self.remote_url:
            raise ValueError('git repo %r does not exist; need remote url' % self.git_dir)
        if os.path.exists(self.work_tree):
            # TODO: we can deal with this; see install_vee.py
            raise ValueError('work tree %r exists without repo' % self.work_tree)
        elif shallow:
            print style('Cloning shallow', 'blue', bold=True), style(self.remote_url, bold=True)
            call(['git', 'clone', '--depth=1', self.remote_url, self.work_tree])
        else:
            print style('Cloning', 'blue', bold=True), style(self.remote_url, bold=True)
            call(['git', 'clone', self.remote_url, self.work_tree])

    def git(self, *cmd, **kw):
        return call(('git', '--git-dir', self.git_dir, '--work-tree', self.work_tree) + cmd, **kw)

    def assert_remote_name(self, name=None):
        name = name or self.remote_name
        self.git('config', 'remote.%s.url' % name, self.remote_url, silent=True)
        self.git('config', 'remote.%s.fetch' % name, '+refs/heads/*:refs/remotes/%s/*' % name, silent=True)
        return name

    def rev_parse(self, revision, fetch=None, remote=None):

        remote = remote or self.remote_url

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
                print style('Fetching shallow', 'blue', bold=True), style(remote, bold=True)
                self.git('fetch', '--update-shallow', remote, silent=True)
                commit = self._rev_parse(revision)

                # Lets get the whole history.
                if not commit:
                    print style('Fetching unshallow', 'blue', bold=True), style(remote, bold=True)
                    self.git('fetch', '--unshallow', remote, silent=True)
                    commit = self._rev_parse(revision)

            else:
                # Normal fetch here.
                print style('Fetching', 'blue', bold=True), style(remote, bold=True)
                self.git('fetch', remote, silent=True)
                commit = self._rev_parse(revision)

        if not commit:
            msg = 'revision %r does not exist in %s' % (revision, remote)
            raise ValueError(msg)

        return commit

    def _rev_parse(self, original_name):

        git_dir = self.git_dir

        name = original_name
        res = None
        visited = set()
        while not res or not re.match(r'^[0-9a-f]{40}$', res):
            
            if res and res.startswith('ref:'):
                name = res[4:].strip()
            
            if name in visited:
                raise ValueError('recursion in refs: %r at %r' % (name, res))
            visited.add(name)
            
            for path_parts in [
                (git_dir, name),
                (git_dir, 'refs/heads', name),
                (git_dir, 'refs/remotes', name),
            ]:
                path = os.path.join(*path_parts)
                if os.path.exists(path):
                    res = open(path).read().strip()
                    break
            else:
                # Warn?
                res = self.git('rev-parse', '--verify', '--quiet', original_name, silent=True, stdout=True).strip()
        
        return res or None

    def _current_head(self):
        self._head = self.rev_parse('HEAD')
        return self._head

    @property
    def head(self):
        return self._head or self._current_head()

    @property
    def is_shallow(self):
        return os.path.exists(os.path.join(self.git_dir, 'shallow'))

    def status(self):
        # We use the machine-parsable git status.
        encoded = self.git('status', '-z', stdout=True, silent=True)
        # In theory, there can be a second NULL-terminated field, but I
        # haven't seen it yet.
        parts = encoded.split('\0')
        for part in parts:
            if not part:
                continue
            idx  = part[0].strip()
            tree = part[1].strip()
            name = part[3:]
            yield (idx, tree, name)

    def distance(self, left, right):
        out = self.git('rev-list', '--left-right', '--count', '%s...%s' % (left, right), silent=True, stdout=True)
        m = re.match(r'^\s*(\d+)\s+(\d+)\s*$', out)
        if not m:
            print 'Could not get distance'
            # Warn here?
            return (0, 0)
        return int(m.group(1)), int(m.group(2))

    def fetch(self, rev='origin/master', remote=None):
        return self.rev_parse(rev, fetch=True, remote=remote)

    def checkout(self, revision, fetch=None):
        commit = self.rev_parse(revision, fetch=fetch)
        if self.head != commit:
            print style('Checking out', 'blue', bold=True), style('%s [%s]' % (revision, commit), bold=True)
            self.git('reset', '--hard', commit, silent=True)
            self.git('submodule', 'update', '--init', '--recursive', silent=True)
            self._head = commit




