import collections

from vee.package import Package
from vee.exceptions import AlreadyInstalled, AlreadyLinked, PipelineError, print_cli_exc
from vee import log
from vee.cli import style
from vee.utils import guess_name


class PackageSet(collections.OrderedDict):

    def __init__(self, env=None, home=None):
        super(PackageSet, self).__init__()
        self.env = env
        self.home = home

        self._parent_names = {}

        self._extracted = set()
        self._installed = set()
        self._deferred = set()
        self._persisted = set()
        self._linked = set()
        self._errored = set()

    def resolve(self, req, check_existing=True, weak=False, env=None):

        # We may need to guess a name.
        name = req.name or guess_name(req.url)
        try:
            return self[name]
        except KeyError:
            pass

        # We don't want to mutate the incoming package, even though we could,
        # because we want to allow others to keep the abstract and concrete
        # packages isolated if they want to.
        pkg = Package(req, set=self, home=self.home)

        # Our guessed name may be wrong after the package is resolved (e.g.
        # deferred packages will definitely be wrong).
        pkg.name = pkg.name or name

        if check_existing:
            (
                pkg.resolve_existing(env=env or self.env) or
                pkg.resolve_existing() or
                (weak and pkg.resolve_existing(weak=True))
            )

        # Store it under the package name since deferred dependencies will not
        # have a name set (in order to load the specific package they were before).
        self[pkg.name] = pkg
        return pkg
    
    def resolve_set(self, req_set, **kwargs):
        for req in req_set.iter_packages():
            self.resolve(req, **kwargs)

    def install(self, names=None, link_env=None, reinstall=False, relink=False, no_deps=False):

        # I'd love to split this method into an "install" and "link" step, but
        # then we'd need to reimplement the dependency resolution. That would
        # be a good idea to do anyways, but... meh.

        if isinstance(names, basestring):
            names = [names]
        names = list(names) if names else self.keys()

        for name in names:
            if name not in self:
                raise KeyError(name)

        if not isinstance(reinstall, set):
            reinstall = set(names if no_deps else self.keys()) if reinstall else set()
        if not isinstance(relink, set):
            relink    = set(names if no_deps else self.keys()) if relink    else set()

        while names:
            name = names.pop(0)

            self._parent_names.setdefault(name, None)
            
            parent_chain = []
            tip = name
            while tip and tip not in parent_chain:
                parent_chain.append(tip)
                tip = self._parent_names.get(tip)
            parent_chain = parent_chain[1:]

            print '==>', style(name, 'blue'), style('(%s)' % ' < '.join(parent_chain), faint=True) if parent_chain else ''

            with log.indent():

                # Avoid infinite error loops.
                if name in self._errored:
                    log.warning('Skipping due to previous error.')
                    continue

                try:
                    self._install_one(names, name, link_env, reinstall, relink, no_deps)
                except PipelineError as e:
                    self._errored.add(name)
                    log.error(str(e))
                    continue
                except Exception as e:
                    self._errored.add(name)
                    print_cli_exc(e, verbose=True)
                    log.exception('Exception while processing %s' % name)
                    continue

        if self._errored:
            log.warning('There were errors in: %s' % ', '.join(sorted(self._errored)))


    def _install_one(self, names, name, link_env, reinstall, relink, no_deps):

        try:
            pkg = self[name]
        except KeyError:
            print ', '.join(sorted(self.keys()))
            raise

        reinstall_this = name in reinstall
        relink_this    = name in relink

        if name not in self._extracted:
            try:
                # Between every step, take a look to see if we now have
                # enough information to tell that it is already installed.
                pkg.assert_uninstalled(uninstall=reinstall_this)
                pkg.pipeline.run_to('fetch')
                pkg.assert_uninstalled(uninstall=reinstall_this)
                pkg.pipeline.run_to('extract')
                pkg.assert_uninstalled(uninstall=reinstall_this)
                pkg.pipeline.run_to('inspect')
                pkg.assert_uninstalled(uninstall=reinstall_this)
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
        for i, dep in ([] if no_deps else enumerate(pkg.dependencies)):

            # Since resolution is rather loose in here (only by name, not URL)
            # we want to replace dependencies with their concrete variant to
            # ease recording that into the database. 
            dep = self.resolve(dep, weak=True)
            pkg.dependencies[i] = dep
            self._parent_names.setdefault(dep.name, pkg.name)

            # We must check if the dependency errored, otherwise we will still
            # end up in an infinite loop.
            if dep.name in self._errored:
                log.warning('Skipping due to error in %s' % dep.name)
                self._errored.add(pkg.name)
                return

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
            return

        pre_build_deps = pkg.dependencies[:]

        if name not in self._installed:
            try:
                pkg.pipeline.run_to('build')
                pkg.pipeline.run_to('install')
                pkg.pipeline.run_to('relocate')
            except AlreadyInstalled:
                pass
            pkg.pipeline.run_to('optlink')
            self._installed.add(name)

        # We need to build/install Homebrew packages before we can decide
        # which of their optional dependencies will be used. The relocation
        # process can also determine other dependencies. We need to run
        # these new ones through the pipe too.
        if pkg.dependencies != pre_build_deps:
            log.debug('%s has changed dependencies after build/install')
            names.insert(insert_i, name)
            return

        if name not in self._persisted:

            # We need to wait to persist until all dependencies are
            # installed.
            if not deps_installed:
                log.debug('%s cannot persist without all dependencies' % (name, ))
                names.insert(insert_i, name)
                return

            pkg.persist_in_db()
            pkg.shared_libraries() # TODO: Move this earlier?
            self._persisted.add(name)

        if link_env and name not in self._linked:
            try:
                pkg.link(link_env, force=relink_this)
            except AlreadyLinked:
                pass
            self._linked.add(name)


