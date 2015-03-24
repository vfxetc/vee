import collections

from vee.requirement import Requirement
from vee.packages import make_package
from vee.exceptions import AlreadyInstalled, AlreadyLinked
from vee import log


class PackageSet(collections.OrderedDict):

    def __init__(self, env=None, home=None):
        super(PackageSet, self).__init__()
        self.env = env
        self.home = home

        self._extracted = set()
        self._installed = set()
        self._linked = set()

    def resolve(self, req, check_existing=True, env=None):
        if req.name not in self:
            self[req.name] = pkg = make_package(req, home=self.home)
            if check_existing:
                pkg.resolve_existing(env=env or self.env)
        return self[req.name]
    
    def resolve_set(self, req_set, **kwargs):
        for req in req_set.iter_requirements():
            self.resolve(req, **kwargs)

    def auto_install(self, names=None, force=False, link_env=None, force_link=False):

        if isinstance(names, basestring):
            names = [names]
        names = self.keys() if names is None else list(names)

        while names:

            name = names.pop(0)

            pkg = self.get(name)
            if not pkg:
                raise KeyError(name)

            if name not in self._extracted:
                try:
                    pkg._reinstall_check(force)
                    pkg.fetch()
                    pkg._reinstall_check(force)
                    pkg.extract()
                    pkg.inspect()
                    pkg._reinstall_check(force)
                except AlreadyInstalled:
                    self._installed.add(name)
                finally:
                    self._extracted.add(name)

            # Loop around for dependencies.
            waiting_for_deps = 0
            for dep_req in pkg.dependencies:
                dep_pkg = self.resolve(dep_req)
                if dep_pkg.name not in self._installed:
                    log.debug('%s needs %s, which is not yet checked' % (name, dep_pkg.name))
                    names.insert(waiting_for_deps, dep_pkg.name)
                    waiting_for_deps += 1
            if waiting_for_deps:
                names.insert(waiting_for_deps, name)
                continue

            if name not in self._installed:
                pkg.build()
                pkg.install()
                pkg.db_id()
                pkg.shared_libraries()
                self._installed.add(name)

            if link_env and name not in self._linked:
                try:
                    pkg.link(link_env, force=force_link)
                except AlreadyLinked:
                    pass
                self._linked.add(name)

