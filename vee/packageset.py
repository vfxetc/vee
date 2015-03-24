from vee.requirement import Requirement
from vee.packages import make_package


class PackageSet(dict):

    def __init__(self, env=None, home=None):
        self.env = env
        self.home = home

    def resolve(self, req, check_existing=True, env=None):
        if req.name not in self:
            self[req.name] = pkg = make_package(req, home=self.home)
            if check_existing:
                pkg.resolve_existing(env=env or self.env)
        return self[req.name]
        
