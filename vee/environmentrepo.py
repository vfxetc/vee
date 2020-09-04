from subprocess import CalledProcessError
import os
import re

from vee import log
from vee.cli import style_note, style_warning, style_error, style
from vee.environment import Environment
from vee.exceptions import AlreadyInstalled, AlreadyLinked, PipelineError, print_cli_exc
from vee.exceptions import CliMixin
from vee.git import GitRepo
from vee.manifest import Manifest, Header
from vee.packageset import PackageSet
from vee.solve import solve
from vee.utils import cached_property, makedirs


class EnvironmentRepo(GitRepo):

    def __init__(self, dbrow, home):
        super(EnvironmentRepo, self).__init__(
            work_tree=dbrow['path'] or home._abs_path('repos', dbrow['name']),
            remote_name=dbrow['remote'],
            branch_name=dbrow['branch'],
        )
        self.id = dbrow['id']
        self.name = dbrow['name']
        self.home = home
        self._req_path = os.path.join(self.work_tree, 'manifest.txt')

    def fetch(self):
        return super(EnvironmentRepo, self).fetch(self.remote_name, self.branch_name)

    def checkout(self, force=False):
        super(EnvironmentRepo, self).checkout(
            revision='%s/%s' % (self.remote_name, self.branch_name), 
            branch=self.branch_name,
            force=force
        )

    def get_environment(self):
        return Environment(repo=self, home=self.home)
    
    def load_manifest(self, revision=None):
        manifest = Manifest(repo=self, home=self.home)
        if revision:
            manifest.parse_file(os.path.basename(self._req_path), alt_open=lambda x: self.show(revision, x).splitlines())
        elif os.path.exists(self._req_path):
            manifest.parse_file(self._req_path)
        return manifest

    def dump_manifest(self, req_set):
        return req_set.dump(self._req_path)
    
    def commit(self, message, semver_level=None):

        manifest = self.load_manifest()

        version_header = manifest.headers.get('Version')
        if not version_header:
            version_header = manifest.add_header('Version', '0.0.0')

        if semver_level is not None:
            version = []
            for i, x in enumerate(re.split(r'[.-]', version_header.value)):
                try:
                    version.append(int(x))
                except ValueError:
                    version.append(x)
            while len(version) <= semver_level:
                version.append(0)
            
            version[semver_level] = version[semver_level] + 1
            for i in range(semver_level + 1, len(version)):
                version[i] = 0

            version_header.value = '.'.join(str(x) for x in version)

        from vee import __about__ as about
        manifest.set_header('Vee-Revision', about.__version__ + '+' + about.__revision__)

        paths = self.dump_manifest(manifest)
        for path in paths:
            self.git('add', path, silent=True)

        status = list(self.status())
        if not status:
            raise RuntimeError('nothing to commit')

        # Make sure there are no other changes.
        for idx, tree, name in status:
            if tree.strip():
                raise RuntimeError('work-tree is dirty')

        self.git('commit', '-m', message, silent=True)

    def update(self, force=False):

        log.info(style_note('Updating repo', self.name))

        self.clone_if_not_exists()

        if self.remote_name not in self.remotes():
            log.warning('"%s" does not have remote "%s"' % (self.name, self.remote_name))
            return True

        rev = self.fetch()

        if not force and not self.check_ff_safety(rev):
            log.error('Cannot fast-forward; skipping.')
            return False

        self.checkout(force=force)
        return True

    def upgrade(self, dirty=False, subset=None, reinstall=False, relink=False,
        no_deps=False, force_branch_link=True
    ):

        self.clone_if_not_exists()

        try:
            head = self.head
        except CalledProcessError:
            log.warning('no commits in repository')
            head = None

        try:
            remote_head = self.rev_parse('%s/%s' % (self.remote_name, self.branch_name))
        except ValueError:
            log.warning('tracked %s/%s does not exist in self' % (self.remote_name, self.branch_name))
            remote_head = None

        if remote_head and head != remote_head:
            log.warning('%s repo not checked out to %s/%s' % (
                self.name, self.remote_name, self.branch_name))

        dirty = bool(list(self.status()))
        if not dirty and self.is_dirty():
            log.error('%s repo is dirty; force with --dirty' % self.name)
            return False

        # '''
        manifest = self.load_manifest()
        to_install = []

        for pkg in manifest.iter_packages():

            if not reinstall:
                pkg.resolve_existing()

            for var in pkg.flattened():

                # Use this as a signal for it being installed instead of pkg.installed
                # because we don't need to reinstall old false variants.
                if var.id and not reinstall:
                    continue

                to_install.append(var)

        installed = set()
        extracted = set()

        while to_install:

            var = to_install.pop(0)

            if var in installed:
                continue
            if var.installed:
                installed.add(var)
                continue

            sol = solve(var.requires, manifest)

            ok = True
            for dep in sol.values():
                
                if var is dep:
                    continue
                if dep in installed:
                    continue
                if dep.installed:
                    installed.add(dep)
                    continue

                ok = False
                break

            if not ok:
                to_install.extend(sol.values())
                to_install.append(var)
                continue

            print("INSTALLING", var)
            try:
                reinstall_this = False
                # Between every step, take a look to see if we now have
                # enough information to tell that it is already installed.
                var.assert_uninstalled(uninstall=reinstall_this)
                var.pipeline.run_to('fetch')
                var.assert_uninstalled(uninstall=reinstall_this)
                var.pipeline.run_to('extract')
                var.assert_uninstalled(uninstall=reinstall_this)
                var.pipeline.run_to('inspect')
                var.assert_uninstalled(uninstall=reinstall_this)
            except AlreadyInstalled:
                installed.add(var)
            finally:
                extracted.add(var)

