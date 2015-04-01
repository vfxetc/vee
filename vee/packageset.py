import collections

from vee.package import Package
from vee.exceptions import AlreadyInstalled, AlreadyLinked
from vee import log


class PackageSet(collections.OrderedDict):

    def __init__(self, env=None, home=None):
        super(PackageSet, self).__init__()
        self.env = env
        self.home = home

        self._extracted = set()
        self._installed = set()
        self._deferred_by_deps = set()
        self._linked = set()

    def resolve(self, req, check_existing=True, env=None):
        if req.name not in self:
            self[req.name] = pkg = Package(req, home=self.home)
            if check_existing:
                pkg.resolve_existing(env=env or self.env) or pkg.resolve_existing()
        return self[req.name]
    
    def resolve_set(self, req_set, **kwargs):
        for req in req_set.iter_packages():
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

            # Loop around for dependencies. We insert dependencies, and the
            # package itself, back into the names to check. If we get back to
            # a name that we have already deferred in this manner, we continue
            # anyways, since that means there is a dependency cycle. We assume
            # that dependency order is resolved in the requirements file.
            waiting_for_deps = 0
            for dep_req in pkg.dependencies:
                dep_pkg = self.resolve(dep_req)
                if dep_pkg.name not in self._installed:
                    key = (name, dep_pkg.name)
                    if key in self._deferred_by_deps:
                        log.debug('%s needs %s, but was already deferred' % (name, dep_pkg.name))
                    else:
                        log.debug('%s needs %s, which is not yet checked' % (name, dep_pkg.name))
                        names.insert(waiting_for_deps, dep_pkg.name)
                        waiting_for_deps += 1
                        self._deferred_by_deps.add(key)
            if waiting_for_deps:
                names.insert(waiting_for_deps, name)
                continue

            if name not in self._installed:
                pkg.build()
                try:
                    pkg.install()
                except AlreadyInstalled:
                    pass
                pkg.persist_in_db()
                pkg.shared_libraries()
                self._installed.add(name)

            if link_env and name not in self._linked:
                try:
                    pkg.link(link_env, force=force_link)
                except AlreadyLinked:
                    pass
                self._linked.add(name)

