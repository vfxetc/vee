import os
import pkg_resources

from vee.config import Config
from vee.database import Database
from vee.environmentrepo import EnvironmentRepo
from vee.git import GitRepo
from vee.utils import makedirs, cached_property


# We shall call the default repository "primary", as it is a nice generic name
# and it does not start with any other letters in the path:
# $VEE/environments/primary/refs/origin/master
PRIMARY_REPO = 'primary'


class Home(object):

    def __init__(self, root=None, repo=None):

        self.root = os.environ.get('VEE') if root is None else root
        if self.root is None:
            raise ValueError('need a root, or $VEE')

        self.default_repo_name = repo if repo is not None else os.environ.get('VEE_REPO')

        self.db = Database(self._abs_path('vee-index.sqlite'))
        self.config = Config(self)

    @cached_property
    def dev_root(self):
        env_value = os.environ.get('VEE_DEV')
        return env_value if env_value is not None else self._abs_path('dev')

    def init(self, url=None, name=None, is_default=True):
        self._makedirs()
        if url:
            env_repo = self.clone_env_repo(
                url=url,
                name=name or self.default_repo_name or PRIMARY_REPO,
                is_default=is_default
            )

    def _abs_path(self, *args):
        return os.path.abspath(os.path.join(self.root, *args))

    def _makedirs(self):
        for name in ('builds', 'environments', 'installs', 'packages', 'repos'):
            path = self._abs_path(name)
            makedirs(path)

    def get_env_repo(self, name=None):

        name = name or self.default_repo_name

        if name:
            # If directly named, the repo must exist.
            git_repo = GitRepo(self._abs_path('repos', name))
            if not git_repo.exists:
                raise ValueError('%r repo does not exist' % name)
            row = self.db.execute('SELECT * FROM repositories WHERE name = ?', [name]).fetchone()
        else:
            row = self.db.execute('SELECT * FROM repositories WHERE is_default').fetchone()

        if not row:
            raise ValueError('%s repo does not exist' % (repr(name) if row else 'default'))
        
        env_repo = EnvironmentRepo(row, home=self)
        if not env_repo.exists:
            raise ValueError('%r repo does not exist' % env_repo.name)
        return env_repo

    def clone_env_repo(self, url, name=None, remote=None, branch=None, is_default=None):

        name or re.sub(r'\.git$', '', os.path.basename(url))

        # Make sure it doesn't exist.
        try:
            env_repo = self.get_env_repo(name)
        except ValueError:
            pass
        else:
            raise ValueError('%r repo already exists' % name)

        con = self.db.connect()
        cur = con.execute('INSERT INTO repositories (name, remote, branch, is_default) VALUES (?, ?, ?, ?)', [
                          name, remote or 'origin', branch or 'master', bool(is_default)])
        row = con.execute('SELECT * FROM repositories WHERE id = ?', [cur.lastrowid]).fetchone()

        env_repo = EnvironmentRepo(row, home=self)
        env_repo.clone_if_not_exists(url)
        con.execute('UPDATE repositories SET remote = ?, branch = ?, is_default = ?', [
            env_repo.remote_name,
            env_repo.branch_name,
            int(bool(is_default or row['is_default']))
        ])

    def update_env_repo(self, name, url=None, remote=None, branch=None, is_default=None):

        if not (url or remote or branch or is_default):
            raise ValueError('provide something to update')

        env_repo = self.get_env_repo(name)

        if remote or branch or is_default:
            env_repo.remote_name = remote or env_repo.remote_name
            env_repo.branch_name = branch or env_repo.branch_name
            self.db.execute('UPDATE repositories SET remote = ?, branch = ?, is_default = ? WHERE id = ?', [
                env_repo.remote_name,
                env_repo.branch_name,
                int(bool(is_default or row['is_default'])),
                env_repo.id,
            ])
        if url:
            env_repo.remotes(**{env_repo.remote_name: url})

    def main(self, args, environ=None, **kwargs):

        from vee.commands.main import main

        environ = (environ or os.environ).copy()
        environ['VEE'] = self.root

        return main(args, environ, **kwargs)


    def get_development_record(self, input, paths=True):
        con = self.db.connect()

        # Look by name.
        for row in con.execute('SELECT * FROM dev_packages WHERE name = ?', [input]):
            if os.path.exists(row['path']):
                return row

        if not paths:
            return
        # Look by path.
        path = os.path.abspath(input)
        for row in con.execute('SELECT * FROM dev_packages WHERE path = ? OR ? LIKE (path || "/%")', [path, path]):
            if os.path.exists(row['path']):
                return row


