import os
import pkg_resources


from vee.index import Index


class Home(object):

    def __init__(self, root, repo=None):
        self.root = root
        self.repo = repo
        self.index = Index(os.path.join(root, 'vee-index.db'))

    def get_manager(self, name=None, requirement=None):
        name = name or requirement.manager_name
        ep = next(pkg_resources.iter_entry_points('vee_default_managers', name), None)
        if ep:
            return ep.load()(requirement, home=self)
        # TODO: look in repository.
        raise ValueError('unknown manager %r' % name)

    def abspath(self, *args):
        return os.path.abspath(os.path.join(self.root, *args))

