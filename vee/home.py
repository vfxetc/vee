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
        self.db = Database(self.abspath('.vee-db.sqlite'))
        self.config = Config(self)
        self._repo_args = {}

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

        if name not in self._repo_args:
            real_name = self.config.get('repo.default.name', PRIMARY_REPO) if name is None else name
            url = url or self.config['repo.%s.url' % real_name]
            remote_name = self.config.get('repo.%s.remote' % real_name, 'origin')
            branch_name = self.config.get('repo.%s.branch' % real_name, 'master')
            self._repo_args[name] = (real_name, self.abspath('repos', real_name), url, remote_name, branch_name)
        
        real_name, work_tree, url, remote_name, branch_name = self._repo_args[name]
        repo = GitRepo(work_tree, url, remote_name=remote_name, branch_name=branch_name)
        repo.name = real_name
        return repo

    def iter_repos(self):
        for key, url in sorted(self.config.iteritems(glob='repo.*.url')):
            name = key.split('.')[1]
            yield self.get_repo(name, url)

