import os
import pkg_resources


class Home(object):

    def __init__(self, root, repo=None):
        self.root = root
        self.repo = repo

    def get_manager(self, name=None, package=None):
        name = name or package.manager_name
        ep = next(pkg_resources.iter_entry_points('vee_default_managers', name), None)
        if ep:
            return ep.load()(package, home=self)
        # TODO: look in repository.
        raise ValueError('unknown manager %r' % name)

    def abspath(self, *args):
        return os.path.abspath(os.path.join(self.root, *args))
