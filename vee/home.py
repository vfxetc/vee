import os
import pkg_resources

from vee.config import Config
from vee.database import Database
from vee.git import GitRepo


class Home(object):

    def __init__(self, root):
        self.root = root
        self.db = Database(self.abspath('.vee-db.sqlite'))
        self.config = Config(self)
        self._repo_args = {}

    def get_package(self, type=None, requirement=None):
        type = type or requirement.type
        ep = next(pkg_resources.iter_entry_points('vee_package_types', type), None)
        if ep:
            return ep.load()(requirement, home=self)
        # TODO: look in repository.
        raise ValueError('unknown package type %r' % type)

    def abspath(self, *args):
        return os.path.abspath(os.path.join(self.root, *args))

    def get_repo(self, name=None):
        if name not in self._repo_args:
            real_name = self.config.get('repo.default.name', 'master') if name is None else name
            url = self.config['repo.%s.url' % real_name]
            self._repo_args[name] = (self.abspath('.vee-repos', real_name), url)
        return GitRepo(*self._repo_args[name])
