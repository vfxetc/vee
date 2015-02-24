import os
import pkg_resources


from vee.database import Database
from vee.config import Config


class Home(object):

    def __init__(self, root, repo=None):
        self.root = root
        self.repo = repo
        self.db = Database(os.path.join(root, '.vee.sqlite'))
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
