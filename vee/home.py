import os
import pkg_resources

from vee.config import Config
from vee.database import Database
from vee.git import GitRepo


class Home(object):

    def __init__(self, root):
        self.root = root
        self.repo = GitRepo(self.abspath('.vee-repo'))
        self.db = Database(self.abspath('.vee-db.sqlite'))
        self.config = Config(self)

    def get_package(self, type=None, requirement=None):
        type = type or requirement.type
        ep = next(pkg_resources.iter_entry_points('vee_package_types', type), None)
        if ep:
            return ep.load()(requirement, home=self)
        # TODO: look in repository.
        raise ValueError('unknown package type %r' % type)

    def abspath(self, *args):
        return os.path.abspath(os.path.join(self.root, *args))
