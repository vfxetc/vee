from subprocess import CalledProcessError
import os
import re

from vee import log
from vee.cli import style_note, style_warning, style_error, style
from vee.environment import Environment
from vee.exceptions import CliMixin
from vee.git import GitRepo
from vee.packageset import PackageSet
from vee.requirements import Requirements, Header
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
        self._req_path = os.path.join(self.work_tree, 'requirements.txt')

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
    
    def load_requirements(self, revision=None):
        reqs = Requirements(env_repo=self, home=self.home)
        if revision:
            reqs.parse_file(os.path.basename(self._req_path), alt_open=lambda x: self.show(revision, x).splitlines())
        elif os.path.exists(self._req_path):
            reqs.parse_file(self._req_path)
        return reqs

    def dump_requirements(self, req_set):
        return req_set.dump(self._req_path)
    
    def commit(self, message, semver_level=None):

        req_set = self.load_requirements()

        version_header = req_set.headers.get('Version')
        if not version_header:
            version_header = req_set.add_header('Version', '0.0.0')

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
        req_set.set_header('Vee-Revision', about.__version__ + '+' + about.__revision__)

        paths = self.dump_requirements(req_set)
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

        env = self.get_environment()

        req_set = self.load_requirements()
        pkg_set = PackageSet(env=env, home=self.home)
        
        # Register the whole set, so that dependencies are pulled from here instead
        # of weakly resolved from installed packages.
        # TODO: This blanket reinstalls things, even if no_deps is set.
        pkg_set.resolve_set(req_set, check_existing=not reinstall)

        # Install and/or link.
        pkg_set.install(subset or None, link_env=env, reinstall=reinstall, relink=relink, no_deps=no_deps)

        if pkg_set._errored and not force_branch_link:
            log.warning("Not creating branch or version links; force with --force-branch-link")
            return False

        # Create a symlink by branch.
        path_by_branch = self.home._abs_path('environments', self.name, self.branch_name)
        if os.path.lexists(path_by_branch):
            os.unlink(path_by_branch)
        makedirs(os.path.dirname(path_by_branch))
        os.symlink(env.path, path_by_branch)

        # Create a symlink by version.
        version = req_set.headers.get('Version')
        if version:
            path_by_version = self.home._abs_path('environments', self.name, 'versions', version.value + ('-dirty' if dirty else ''))
            if os.path.lexists(path_by_version):
                os.unlink(path_by_version)
            makedirs(os.path.dirname(path_by_version))
            os.symlink(env.path, path_by_version)

        return True
