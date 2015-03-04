import os
import pkg_resources

from vee.config import Config
from vee.database import Database
from vee.git import GitRepo
from vee.utils import makedirs
from vee.requirementrepo import RequirementRepo


# We shall call the default repository "primary", as it is a nice generic name
# and it does not start with any other letters in the path:
# $VEE/environments/primary/refs/origin/master
PRIMARY_REPO = 'primary'


class Home(object):

    def __init__(self, root):
        self.root = root
        self.db = Database(self._abs_path('vee-index.sqlite'))
        self.config = Config(self)
        self._repo_rows = {}

    def init(self, url=None, name=PRIMARY_REPO):
        self._makedirs()
        if not url:
            return
        con = self.db.connect()
        row = con.execute('SELECT id FROM repositories WHERE name = ?', [name]).fetchone()
        if row:
            con.execute('UPDATE repositories SET url = ? WHERE id = ?', [url, row['id']])
        else:
            con.execute('INSERT INTO repositories (name, url, is_default) VALUES (?, ?, ?)', [name, url, True])

    def _abs_path(self, *args):
        return os.path.abspath(os.path.join(self.root, *args))

    def _makedirs(self):
        for name in ('builds', 'environments', 'installs', 'packages', 'repos'):
            path = self._abs_path(name)
            makedirs(path)

    def get_repo(self, name=None, url=None):
        if name not in self._repo_rows:
            con = self.db.connect()
            if name is None:
                row = con.execute('SELECT * FROM repositories WHERE is_default LIMIT 1').fetchone()
                row = row or con.execute('SELECT * FROM repositories LIMIT 1').fetchone()
            else:
                row = con.execute('SELECT * FROM repositories WHERE name = ?', [name]).fetchone()
            self._repo_rows[name] = row
        row = self._repo_rows[name]
        if not row:
            raise ValueError('%s repo does not exist' % (repr(name) if row else 'default'))

        return RequirementRepo(
            self._abs_path('repos', row['name']),
            url or row['url'],
            remote_name='origin',
            branch_name=row['branch'],
        )

    def main(self, args, environ=None, **kwargs):

        from vee.commands.main import main

        environ = (environ or os.environ).copy()
        environ['VEE'] = self.root

        return main(args, environ, **kwargs)

    @property
    def dev_root(self):
        return self._abs_path(os.environ.get('VEE_DEV', 'dev'))

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


