from subprocess import CalledProcessError
import glob
import os
import re
import subprocess

from vee.cli import style
from vee.subproc import call
from vee.exceptions import CliException


class GitError(CliException):
    pass


def normalize_git_url(url, prefix=False):

    if not isinstance(prefix, basestring):
        prefix = 'git+' if prefix else ''

    # Strip fragments.
    url = re.sub(r'#.*$', '', url)

    # The git protocol.
    m = re.match(r'^(?:git\+)?git:(//)?(.+)$', url)
    if m:
        return 'git://' + m.group(2)

    # Assert prefix on ssh and http urls. Note: this accepts at least all of
    # the schemes that git does.
    m = re.match(r'^(?:git\+)?(\w+):(.+)$', url)
    if m:
        scheme, the_rest = m.groups()
        return '%s%s:%s' % (prefix, scheme, the_rest)

    # Direct paths. This one MUST have the git+ on the front in order to be
    # detected by this method.
    m = re.match(r'^git\+(/.+)$', url)
    if m:
        return '%s%s' % (prefix, m.group(1))

    # SCP-like.
    m = re.match(r'^(?:git\+)?([^:@]+@)?([^:]+):(.*)$', url)
    if m:
        userinfo, host, path = m.groups()
        return '%s%s%s:%s' % (prefix, userinfo or '', host, path.rstrip('/'))



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

    def git(self, *cmd, **kw):

        stderr = []
        if kw.get('on_stderr'):
            raise NotImplementedError('cant nest on_stderr (yet)')
        kw['on_stderr'] = stderr.append

        try:
            # If we can, run as if we are within the work tree.
            if self.work_tree and self.git_dir == os.path.join(self.work_tree, '.git'):
                kw['cwd'] = self.work_tree
                res = call(('git', ) + cmd, **kw)
            else:
                res = call(('git', '--git-dir', self.git_dir, '--work-tree', self.work_tree) + cmd, **kw)

        except CalledProcessError:
            fatal = next((line for line in stderr if line.startswith('fatal:')), None)
            if fatal:
                fatal = fatal.splitlines()[0][6:].strip()
                raise GitError(fatal, detail=''.join(stderr).rstrip())
            raise

        return res

    def clone_if_not_exists(self, remote_url=None, shallow=True):
        self.remote_url = remote_url or self.remote_url
        if self.exists:
            return
        if not self.remote_url:
            raise ValueError('git repo %r does not exist; need remote url' % self.git_dir)
        # if os.path.exists(self.work_tree):
            # TODO: we can deal with this; see install_vee.py
            # raise ValueError('work tree %r exists without repo' % self.work_tree)
        if shallow:
            print style('Cloning shallow', 'blue', bold=True), style(self.remote_url, bold=True)
            call(['git', 'clone', '--depth=1', self.remote_url, self.work_tree])
        else:
            print style('Cloning', 'blue', bold=True), style(self.remote_url, bold=True)
            call(['git', 'clone', self.remote_url, self.work_tree])

    def assert_remote_url(self, name=None):
        """Make sure our remote URL is what we think it is."""
        name = name or self.remote_name
        self.git('config', 'remote.%s.url' % name, self.remote_url, silent=True)
        self.git('config', 'remote.%s.fetch' % name, '+refs/heads/*:refs/remotes/%s/*' % name, silent=True)
        return name

    def rev_parse(self, revision, fetch=None, remote=None):
        """Parse a commit-ish into a commit.

        This is undefined for hash revisions.

        :param revision: The commit-ish to parse.
        :param fetch: Should we fetch if we don't have the revision?
        :param remote: The remote to fetch from.

        """

        remote = remote or self.remote_url

        if fetch:
            self.clone_if_not_exists(shallow=True)

        commit = self._rev_parse(revision)
        if commit:
            return commit

        if not fetch:
            raise ValueError('revision %r does not exist in local repo' % revision)

        commit = self.fetch(remote, revision)
        if commit:
            return commit

        msg = 'revision %r does not exist in %s' % (revision, remote)
        raise ValueError(msg)

    def _rev_parse(self, reference, fallback=True):

        git_dir = self.git_dir
        rev = reference
        seen = set()

        while not re.match(r'^[0-9a-f]{40}', rev):

            if rev in seen:
                raise ValueError('recursion in refs: %r' % rev)
            seen.add(rev)
            
            for path_parts in [
                (git_dir, rev),
                (git_dir, 'refs/heads', rev),
                (git_dir, 'refs/remotes', rev),
            ]:
                path = os.path.join(*path_parts)
                if os.path.exists(path):
                    rev = open(path).read().strip()
                    if rev.startswith('ref:'):
                        rev = rev[4:].strip()
                    break

            else:

                # Glob into the objects.
                m = re.match(r'^[0-9a-f]{8,40}(\s|$)', rev)
                if m:
                    hash_ = m.group(1)
                    paths = glob.glob(os.path.join(git_dir, 'objects', hash_[:2], hash_[2:] + '*'))
                    if len(paths) == 1:
                        rev = hash_[:2] + os.path.basename(paths[0])
                        continue

                # Finally, let git try.
                if fallback:
                    rev = self.git('rev-parse', '--verify', '--quiet', reference, silent=True, stdout=True).strip()
                
                break
        
        return rev[:40] if rev and re.match(r'^[0-9a-f]{40}', rev) else None

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
        """Get a series of (index_status, work_tree_status, filename) tuples."""
        # We use the machine-parsable git status.
        encoded = self.git('status', '-z', stdout=True, silent=True)
        # In theory, there can be a second NULL-terminated field, but I
        # haven't seen it yet.
        parts = encoded.split('\0')
        res = []
        for part in parts:
            if not part:
                continue
            idx  = part[0].strip()
            tree = part[1].strip()
            name = part[3:]
            res.append((idx, tree, name))
        return res

    def distance(self, left, right, strict=True):
        out = self.git('rev-list', '--left-right', '--count', '%s...%s' % (left, right), silent=True, stdout=True)
        m = re.match(r'^\s*(\d+)\s+(\d+)\s*$', out)
        if not m:
            if strict:
                raise ValueError('could not get distance from %r to %r' % (left, right))
            return (0, 0)
        return int(m.group(1)), int(m.group(2))

    def fetch(self, remote=None, ref=None, shallow=True):

        remote = remote or self.remote_url

        if ref:
            if re.match(r'\w+', remote):
                revision = '%s/%s' % (remote, ref)
            else:
                revision = 'FETCH_HEAD'
        ref_args = (ref, ) if ref else ()

        if self.is_shallow:

            # Fetch the new history on top of the shallow history.
            if shallow:
                print style('Fetching shallow', 'blue', bold=True), style(remote, bold=True)
                self.git('fetch', '--update-shallow', remote, *ref_args, silent=True)
                if not revision:
                    return
                commit = self._rev_parse(revision)

            # Lets get the whole history.
            if not shallow or not commit:
                print style('Fetching unshallow', 'blue', bold=True), style(remote, bold=True)
                self.git('fetch', '--unshallow', remote, *ref_args, silent=True)
                commit = self._rev_parse(revision)

        else:
            # Normal fetch here.
            print style('Fetching', 'blue', bold=True), style(remote, bold=True)
            self.git('fetch', remote, *ref_args, silent=True)
            if not revision:
                return
            commit = self._rev_parse(revision)

        return commit

    def checkout(self, revision, branch=None, force=False, fetch=False):

        commit = self.rev_parse(revision, fetch=fetch)
        if self.head == commit:
            return

        print style('Checking out', 'blue', bold=True), style('%s [%s]' % (revision, commit), bold=True)

        cmd = ['checkout']
        if force:
            cmd.append('--force')
        if branch: # Make this branch if it doesn't exist.
            cmd.extend(('-B', branch))
        cmd.append(revision)
        self.git(*cmd, silent=True)
        self.git('submodule', 'update', '--init', '--checkout', '--recursive', silent=False)
        self._head = commit

    def check_ff_safety(self, rev):

        # Check the status of the work tree and index.
        status_ok = True
        for idx, tree, name in self.status():
            if idx or tree:
                print style('Error:', 'red', bold=True), style('uncomitted changes:', bold=True)
                self.git('status', silent=True)
                status_ok = False
                break

        # Make sure we haven't forked.
        ahead, behind = self.distance(self.head, rev)
        if ahead and behind:
            print style('Error:', 'red', bold=True), style('your and the repo have forked', bold=True)
            status_ok = False
        elif ahead:
            print style('Warning:', 'yellow', bold=True), style('you are %s commits ahead of the remote repo; please `vee push`' % ahead, bold=True)
            status_ok = False
        elif behind:
            print style('You are %d commits behind.' % behind, bold=True)

        return status_ok

    def remotes(self, **kwargs):

        remotes = {}
        try:
            lines = self.git('config', '--get-regexp', 'remote.*.url', stdout=True, silent=True).splitlines()
        except CalledProcessError:
            pass
        else:
            for line in lines:
                cname, url = line.strip().split(None, 1)
                _, name, _ = cname.split('.')
                remotes[name] = url

        # Updates!
        if kwargs:
            for k, v in kwargs.iteritems():
                if v is None:
                    if k not in remotes:
                        raise KeyError(k)
                    self.git('remote', 'rm', k, silent=True)
                elif k in remotes:
                    self.git('remote', 'set-url', k, v)
                else:
                    self.git('remote', 'add', k, v)

        return remotes



