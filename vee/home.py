import json
import os
import re

import pkg_resources

from vee.config import Config
from vee.database import Database
from vee.devpackage import DevPackage
from vee.environmentrepo import EnvironmentRepo
from vee.git import GitRepo
from vee.utils import makedirs, cached_property
from vee import log


# We shall call the default repository "primary", as it is a nice generic name
# and it does not start with any other letters in the path:
# $VEE/environments/primary/refs/origin/master
PRIMARY_REPO = 'primary'

DB_NAME = 'vee-index.sqlite'


def default_home_path(environ=None):
    try:
        return (environ or os.environ)['VEE']
    except KeyError:
        return find_home()

def find_home():
    root = os.path.abspath(os.path.join(__file__, '..', '..', '..'))
    while root and root != os.path.sep:
        if os.path.exists(os.path.join(root, DB_NAME)):
            return root
        root = os.path.dirname(root)


class Home(object):

    """The starting point of everything VEE.

    :param str root: The root directory of the home; defaults to ``$VEE``.
    :param str repo: The name of the default repository; defaults to ``$VEE_REPO``.

    """

    def __init__(self, root=None, repo=None):

        if root is None:
            root = default_home()
        if root is None:
            raise ValueError('Need a root, or $VEE.')
        self.root = root

        self.default_repo_name = repo if repo is not None else os.environ.get('VEE_REPO')

        dbpath = self._abs_path(DB_NAME)
        self.db = Database(dbpath)

        self.config = Config(self)

    @property
    def exists(self):
        return self.db.exists

    def init(self, if_not_exists=False, create_parents=False):
        self._makedirs(create_parents) # Do this anyways.
        if self.exists:
            if if_not_exists:
                return
            raise ValueError('home already exists')
        self.db.create()

    @cached_property
    def dev_root(self):
        env_value = os.environ.get('VEE_DEV')
        return os.path.expanduser(env_value) if env_value is not None else self._abs_path('dev')

    @cached_property
    def dev_search_path(self):
        env_value = os.environ.get("VEE_DEV_PATH")
        path = env_value.split(':') if env_value is not None else [self.dev_root]
        path = [os.path.expanduser(x) for x in path]
        return path

    def _abs_path(self, *args):
        return os.path.abspath(os.path.join(self.root, *args))

    def _makedirs(self, create_parents=False):
        if not create_parents and not os.path.exists(os.path.dirname(self.root)):
            raise ValueError('parent of %s does not exist' % self.root)
        for name in ('builds', 'environments', 'installs', 'packages', 'repos'):
            path = self._abs_path(name)
            makedirs(path)

    def iter_development_packages(self, exists=True, search=False):
        paths_seen = set()
        for row in self.db.execute('SELECT * FROM development_packages'):
            dev_pkg = DevPackage(row, home=self)
            # We could check these against paths_seen, but we feel it is better
            # to always return everything that managed to get into the database.
            paths_seen.add(dev_pkg.work_tree)
            # This only detects if the git repo exists, not if the dev_package
            # exists (where new ones may not have repos)
            if dev_pkg.exists:
                yield dev_pkg

        if not search:
            return

        for root in self.dev_search_path:
            if not os.path.exists(root):
                continue
            for name in os.listdir(root):
                if not name.endswith('.vee-dev.json'):
                    continue

                data = json.loads(open(os.path.join(root, name)).read())
                data['id'] = None
                dev_pkg = DevPackage(data, home=self)

                if dev_pkg.work_tree in paths_seen:
                    continue
                paths_seen.add(dev_pkg.work_tree)

                yield dev_pkg

    def iter_env_repos(self):
        for row in self.db.execute('SELECT * FROM repositories'):
            env_repo = EnvironmentRepo(row, home=self)
            if env_repo.exists:
                yield env_repo

    def get_env_repo(self, name=None):
        
        name = name or self.default_repo_name
        
        if name:
            row = self.db.execute('SELECT * FROM repositories WHERE name = ? LIMIT 1', [name]).fetchone()
            if not row:
                raise ValueError('%r repo does not exist' % name)

        else:
            # Grab the default repo if possible, otherwise make sure there is
            # only one.
            rows = self.db.execute('SELECT * FROM repositories ORDER BY is_default DESC LIMIT 2').fetchall()
            if not rows:
                raise ValueError('no repositories exist')
            elif rows[0]['is_default']:
                row = rows[0]
            elif len(rows) == 1:
                row = rows[0]
            else:
                raise ValueError('multiple repositories with no default')
        
        env_repo = EnvironmentRepo(row, home=self)
        if not env_repo.exists:
            log.debug('Looking for env_repo: %s' % env_repo.work_tree)
            raise ValueError('%r repo does not exist' % env_repo.name)
        
        return env_repo

    def create_env_repo(self, path=None, url=None, name=None, remote=None, branch=None, is_default=None):

        if path:
            path = os.path.abspath(path)
            if not os.path.exists(path):
                raise ValueError('no repo at %s' % path)
        
        if url or path:
            name = name or re.sub(r'\.git$', '', os.path.basename(url or path))
        else:
            name = name or self.default_repo_name or PRIMARY_REPO

        # Make sure it doesn't exist.
        try:
            env_repo = self.get_env_repo(name)
        except ValueError:
            pass
        else:
            raise ValueError('%r repo already exists' % name)

        con = self.db.connect()
        cur = con.execute('INSERT OR REPLACE INTO repositories (name, path, remote, branch, is_default) VALUES (?, ?, ?, ?, ?)', [
                          name, path, remote or 'origin', branch or 'master', bool(is_default)])
        row = con.execute('SELECT * FROM repositories WHERE id = ?', [cur.lastrowid]).fetchone()

        env_repo = EnvironmentRepo(row, home=self)
        if url:
            env_repo.clone_if_not_exists(url)
        elif not env_repo.exists:
            makedirs(env_repo.work_tree)
            env_repo.git('init')

        return env_repo

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
        for row in con.execute('SELECT * FROM development_packages WHERE name = ? OR name = ?', [input, os.path.basename(input)]):
            if os.path.exists(row['path']):
                return row

        if not paths:
            return
        # Look by path.
        path = os.path.abspath(input)
        for row in con.execute('SELECT * FROM development_packages WHERE path = ? OR ? LIKE (path || "/%")', [path, path]):
            if os.path.exists(row['path']):
                return row


