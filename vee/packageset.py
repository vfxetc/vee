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
        self._deferred = set()
        self._persisted = set()
        self._linked = set()

    def resolve(self, req, check_existing=True, env=None):

        try:
            return self[req.name]
        except KeyError:
            pass

        # We don't want to mutate the incoming package, even though we could,
        # because we want to allow others to keep the abstract and concrete
        # packages isolated if they want to.
        pkg = Package(req, home=self.home)
        if check_existing:
            (
                pkg.resolve_existing(env=env or self.env) or
                pkg.resolve_existing() or
                pkg.resolve_existing(weak=True)
            )

        # Store it under the package name since deferred dependencies will not
        # have a name set (in order to load the specific package they were before).
        self[pkg.name] = pkg
        return pkg
    
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
            try:
                pkg = self[name]
            except KeyError:
                print self.keys()
                print self[None]
                raise

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
            deferred = False
            deps_installed = True
            insert_i = 0
            for i, dep in enumerate(pkg.dependencies):

                # Since resolution is rather loose in here (only by name, not URL)
                # we want to replace dependencies with their concrete variant to
                # ease recording that into the database. 
                dep = self.resolve(dep)
                pkg.dependencies[i] = dep

                if dep.name not in self._installed:
                    key = (name, dep.name)

                    if key not in self._deferred:
                        log.debug('%s needs %s; deferring install' % (name, dep.name))
                        self._deferred.add(key)
                        deferred = True
                    else:
                        log.debug('%s needs %s, but install was already deferred' % (name, dep.name))

                    deps_installed = False
                    names.insert(insert_i, dep.name)
                    insert_i += 1

            if deferred:
                names.insert(insert_i, name)
                continue

            if name not in self._installed:
                pkg.pipeline.run_to('build')
                try:
                    pkg.pipeline.run_to('install')
                except AlreadyInstalled:
                    pass
                pkg.pipeline.run_to('relocate')
                self._installed.add(name)

            if name not in self._persisted:

                # We need to wait to persist until all dependencies are
                # installed.
                if not deps_installed:
                    log.debug('%s cannot persist without all dependencies' % (name, ))
                    names.insert(insert_i, name)
                    continue

                pkg.persist_in_db()
                pkg.shared_libraries() # TODO: Move this earlier?
                self._persisted.add(name)

            if link_env and name not in self._linked:
                try:
                    pkg.link(link_env, force=relink)
                except AlreadyLinked:
                    pass
                self._linked.add(name)


