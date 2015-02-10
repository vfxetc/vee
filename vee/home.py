import pkg_resources


class Home(object):

    def __init__(self, root, repo=None):
        self.root = root
        self.repo = repo

    def load_manager(self, req):

        ep = next(pkg_resources.iter_entry_points('vee_default_managers', req.manager_name), None)
        if ep:
            return ep.load()(req)

        # TODO: look in repository.

        raise ValueError('unknown manager %r' % req.manager_name)


    def load_requirement(self, req):
        if not req.manager:
            req.manager = self.load_manager(req)
        if not req.package:
            req.package = req.manager.load_package(req)
        return req.manager, req.package
