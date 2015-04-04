import json
import os
import re
import shlex
import sys

from vee import log
from vee.cli import style
from vee.homebrew import Homebrew
from vee.package import Package
from vee.pipeline.base import PipelineStep
from vee.subproc import call
from vee.utils import makedirs, cached_property


class HomebrewManager(PipelineStep):

    factory_priority = 1000

    @classmethod
    def factory(cls, step, pkg):
        if step == 'init' and re.match(r'^homebrew[:+]', pkg.url):
            return cls(pkg)

    def get_next(self, step):
        if step != 'optlink':
            return self

    def init(self):

        pkg = self.package
        pkg.package_name = re.sub(r'^(git\+)?homebrew[:+]', '', pkg.url)
        pkg.url = 'homebrew:' + pkg.package_name

        self.brew = Homebrew(home=pkg.home)
        pkg.package_path = self.brew.cellar

        self.repo = self.brew.repo

        # Parse the requested reversion into a package version, and repo revision.
        # (The version is ignored.)
        self.version = self.revision = None
        if pkg.revision:

            m = re.match(r'^(.+?)(?:\+([0-9a-f]{8,}))?$', pkg.revision)
            if m:
                self.version, self.revision = m.groups()

            # If it looks like only a sha1, then it is the repo revision.
            if self.version and not self.revision and re.match(r'^[0-9a-f]{8,}$', self.version):
                self.revision = self.version
                self.version = None

        # TODO: immediately check info to see if we can satisfy the revision
        # with what is installed, and set install_path accordingly.

    def fetch(self):

        pkg = self.package

        self.repo.clone_if_not_exists()

        # NOTE: Since dependencies may be at a different revision, and the
        # pipelines get processed in parallel, we should really run this
        # checkout before every interaction with Homebrew.
        self.repo.checkout(self.revision or 'HEAD', fetch=True)
        self.revision = self.repo.head[:8]


    def inspect(self):
        self._update_dependencies(optional=False)

    def _update_dependencies(self, optional=True, must_exist=False):
        pkg = self.package
        existing = {}
        for dep in pkg.dependencies:
            existing[dep.name] = dep
        cmd = ['deps', '--1', '--skip-build']
        if not optional:
            cmd.append('--skip-optional')
        cmd.append(pkg.package_name)
        for name in self.brew(*cmd, stdout=True).strip().split():
            if name in existing:
                continue
            if must_exist:
                path = os.path.join(self.brew.cellar, name)
                if not os.path.exists(path):
                    continue
            dep = Package(name=name, url='homebrew:' + name, home=pkg.home)
            pkg.dependencies.append(dep)
            existing[name] = dep
    

    def install_name_from_info(self, name, info=None):
        # TODO: This should return "HEAD" if built with `--head`.
        # TODO: Move this to the Homebrew pipeline step.
        info = info or self.info(name)
        if not info:
            raise ValueError('no homebrew package %s' % name)
        return '%s/%s' % (info['name'], info['linked_keg'] or (
            info['installed'][-1]['version']
            if info['installed']
            else info['versions']['stable']
        ))

    def _set_names(self):

        pkg = self.package

        info = self.brew.info(pkg.package_name)
        self.version = info['linked_keg'] or (
            info['installed'][-1]['version'] if info['installed'] else info['versions']['stable']
        )

        pkg.build_name = pkg.install_name = os.path.join(pkg.package_name,
            'HEAD' if '--HEAD' in pkg.config else self.version
        )
        pkg.build_path = pkg.install_path = os.path.join(self.brew.cellar, pkg.install_name)

        pkg.revision = '%s%s+%s' % (
            self.version,
            '-HEAD' if '--HEAD' in pkg.config else '',
            self.revision
        )


    def extract(self):
        pass

    def build(self):

        # TODO: `brew unlink` before installing if already installed?

        pkg = self.package

        # This may throw warnings that it is already installed. Oops.
        self.brew('install', pkg.package_name, *pkg.config)
        self._set_names()

        # Pull in the optional dependencies if they actually exist.
        self._update_dependencies(optional=True, must_exist=True)

    def install(self):
        pass

    def relocate(self):
        pass

