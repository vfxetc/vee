import json
import os
import re

import pkg_resources

from vee.config import Config
from vee.database import Database
from vee.devpackage import DevPackage
from vee.environmentrepo import EnvironmentRepo
from vee.git import GitRepo, get_default_branch
from vee.utils import makedirs, cached_property, find_home, DB_NAME
from vee import log


# We shall call the default repository "primary", as it is a nice generic name
# and it does not start with any other letters in the path:
# $VEE/environments/primary/refs/origin/master
PRIMARY_REPO = 'primary'



class Home(object):

    """The starting point of everything VEE.

    :param str root: The root directory of the home; defaults to ``$VEE``.
    :param str repo: The name of the default repository; defaults to ``$VEE_REPO``.

    """

    def __init__(self, root=None, repo=None):

        if root is None:
            root = find_home()
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

    def iter_development_packages(self, exists=True, search=True):

        if not search:
            # We used to have a development_packages table, and searching was
            # something that had to be requested.
            log.debug("iter_development_packages(..., seach=False) is deprecated.")

        for root in self.dev_search_path:

            if not os.path.exists(root):
                continue

            for name in os.listdir(root):

                path = os.path.join(root, name)

                if name.endswith('.vee-dev.json'):
                    yield DevPackage.from_tag(path, home=self)
                    continue

                # Not used yet.
                sub_path = os.path.join(path, '.vee-dev.json')
                if os.path.exists(sub_path):
                    yield DevPackage.from_tag(sub_path, home=self)

    def find_development_package(self, name):

        paths = [os.path.abspath(name), name]
    
        for root in self.dev_search_path:
            paths.append(os.path.join(root, name))

        if '/' in name:
            name = os.path.basename(name)

        for path in paths:

            if not os.path.exists(path):
                continue
            
            sidecar_path = os.path.join(os.path.dirname(path), '.' + name + '.vee-dev.json')
            if os.path.exists(sidecar_path):
                return DevPackage.from_tag(sidecar_path, home=self)

            # Not used yet.
            subcar_path = os.path.join(path, '.vee-dev')
            if os.path.exists(subcar_path):
                return DevPackage.from_tag(sidecar_path, home=self)

    def iter_repos(self):
        for row in self.db.execute('SELECT * FROM repositories'):
            repo = EnvironmentRepo(row, home=self)
            if repo.exists:
                yield repo

    def get_repo(self, name=None):
        
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
        
        repo = EnvironmentRepo(row, home=self)
        if not repo.exists:
            log.debug('Looking for repo: %s' % repo.work_tree)
            raise ValueError('%r repo does not exist' % repo.name)
        
        return repo

    def create_repo(self, path=None, url=None, name=None, remote=None, branch=None, is_default=None):

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
            repo = self.get_repo(name)
        except ValueError:
            pass
        else:
            raise ValueError('%r repo already exists' % name)

        branch = branch or get_default_branch()

        con = self.db.connect()
        cur = con.execute('INSERT OR REPLACE INTO repositories (name, path, remote, branch, is_default) VALUES (?, ?, ?, ?, ?)', [
                          name, path, remote or 'origin', branch, bool(is_default)])
        row = con.execute('SELECT * FROM repositories WHERE id = ?', [cur.lastrowid]).fetchone()

        repo = EnvironmentRepo(row, home=self)
        if url:
            repo.clone_if_not_exists(url)
        elif not repo.exists:
            makedirs(repo.work_tree)
            repo.git('init')

        if branch != repo.get_current_branch():
            con.execute('UPDATE repositories SET branch = ? WHERE id = ?', [repo.get_current_branch(), repo.id])

        return repo

    def update_repo(self, name, url=None, remote=None, branch=None, is_default=None):

        if not (url or remote or branch or is_default):
            raise ValueError('provide something to update')

        repo = self.get_repo(name)

        if remote or branch or is_default:
            repo.remote_name = remote or repo.remote_name
            repo.branch_name = branch or repo.branch_name
            self.db.execute('UPDATE repositories SET remote = ?, branch = ?, is_default = ? WHERE id = ?', [
                repo.remote_name,
                repo.branch_name,
                int(bool(is_default or row['is_default'])),
                repo.id,
            ])
        if url:
            repo.remotes(**{repo.remote_name: url})

    def main(self, args, environ=None, **kwargs):

        from vee.commands.main import main

        environ = (environ or os.environ).copy()
        environ['VEE'] = self.root

        return main(args, environ, **kwargs)


