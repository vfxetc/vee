import os
import pkg_resources

from vee.config import Config
from vee.database import Database
from vee.git import GitRepo
from vee.utils import makedirs


# We shall call the default repository "primary", as it is a nice generic name
# and it does not start with any other letters in the path:
# $VEE/environments/primary/refs/origin/master
PRIMARY_REPO = 'primary'


class Home(object):

    def __init__(self, root):
        self.root = root
        self.db = Database(self.abspath('vee-index.sqlite'))
        self.config = Config(self)
        self._repo_rows = {}

    def makedirs(self):
        for name in ('builds', 'environments', 'installs', 'packages', 'repos'):
            path = self.abspath(name)
            makedirs(path)

    def get_package(self, type=None, requirement=None):
        type = type or requirement.type
        ep = next(pkg_resources.iter_entry_points('vee_package_types', type), None)
        if ep:
            return ep.load()(requirement, home=self)
        # TODO: look in repository.
        raise ValueError('unknown package type %r' % type)

    def abspath(self, *args):
        return os.path.abspath(os.path.join(self.root, *args))

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
        repo = GitRepo(self.abspath('repos', row['name']), url or row['url'],
            remote_name=row['track_remote'], branch_name=row['track_branch'])
        repo.name = row['name']
        return repo

    def iter_repos(self):
        for key, url in sorted(self.config.iteritems(glob='repo.*.url')):
            name = key.split('.')[1]
            yield self.get_repo(name, url)

    def main(self, args, environ=None, **kwargs):

        from vee.commands.main import main

        environ = (environ or os.environ).copy()
        environ['VEE'] = self.root

        return main(args, environ, **kwargs)



