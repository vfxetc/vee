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
        self._env_repo_cache = {}

        self.db = Database(self._abs_path('vee-index.sqlite'))
        self.config = Config(self)

    @cached_property
    def dev_root(self):
        env_value = os.environ.get('VEE_DEV')
        return env_value if env_value is not None else self._abs_path('dev')

    def init(self, url=None, name=PRIMARY_REPO, is_default=True):
        self._makedirs()
        if not url:
            return
        con = self.db.connect()
        row = con.execute('SELECT id FROM repositories WHERE name = ?', [name]).fetchone()
        if row:
            con.execute('UPDATE repositories SET url = ? WHERE id = ?', [url, row['id']])
        else:
            con.execute('INSERT INTO repositories (name, url, is_default) VALUES (?, ?, ?)', [name, url, is_default])

    def _abs_path(self, *args):
        return os.path.abspath(os.path.join(self.root, *args))

    def _makedirs(self):
        for name in ('builds', 'environments', 'installs', 'packages', 'repos'):
            path = self._abs_path(name)
            makedirs(path)

    def get_env_repo(self, name=None, url=None):

        name = self.default_repo_name if name is None else name
        try:
            return self._env_repo_cache[name]
        except KeyError:
            pass
        
        con = self.db.connect()
        if name is None:
            row = con.execute('SELECT * FROM repositories WHERE is_default LIMIT 1').fetchone()
            row = row or con.execute('SELECT * FROM repositories LIMIT 1').fetchone()
        else:
            row = con.execute('SELECT * FROM repositories WHERE name = ?', [name]).fetchone()
        if not row:
            raise ValueError('%s repo does not exist' % (repr(name) if row else 'default'))

        env_repo = self._env_repo_cache[name] = EnvironmentRepo(
            self._abs_path('repos', row['name']),
            url or row['url'],
            remote_name='origin',
            branch_name=row['branch'],
            home=self,
        )
        return env_repo


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


