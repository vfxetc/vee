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

    def install(self, names=None, link_env=None, reinstall=False, relink=False):

        # I'd love to split this method into an "install" and "link" step, but
        # then we'd need to reimplement the dependency resolution. That would
        # be a good idea to do anyways, but... meh.
        
        if isinstance(names, basestring):
            names = [names]
        names = list(names) if names else self.keys()

        if any(name not in self for name in names):
            raise KeyError(name)

        while names:

            name = names.pop(0)
            pkg = self[name]

            if name not in self._extracted:
                try:
                    # Between every step, take a look to see if we now have
                    # enough information to tell that it is already installed.
                    pkg.assert_uninstalled(uninstall=reinstall)
                    pkg.pipeline.run_to('fetch')
                    pkg.assert_uninstalled(uninstall=reinstall)
                    pkg.pipeline.run_to('extract')
                    pkg.assert_uninstalled(uninstall=reinstall)
                    pkg.pipeline.run_to('inspect')
                    pkg.assert_uninstalled(uninstall=reinstall)
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
                pkg.pipeline.run_to('build')
                try:
                    pkg.pipeline.run_to('install')
                except AlreadyInstalled:
                    pass
                pkg.pipeline.run_to('relocate')
                pkg.persist_in_db()
                pkg.shared_libraries()
                self._installed.add(name)

            if link_env and name not in self._linked:
                try:
                    pkg.link(link_env, force=relink)
                except AlreadyLinked:
                    pass
                self._linked.add(name)


