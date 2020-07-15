import json
import os
import re
import shlex
import sys

from vee import log
from vee.cli import style, style_note
from vee.homebrew import Homebrew
from vee.package import Package
from vee.pipeline.base import PipelineStep
from vee.subproc import call
from vee.utils import makedirs, cached_property
from vee.pipeline.generic import relocate_package


class HomebrewManager(PipelineStep):

    factory_priority = 1000

    @classmethod
    def factory(cls, step, pkg):
        if step == 'init' and re.match(r'^(home)?brew[:+]', pkg.url):
            return cls(pkg)
        if step == 'relocate' and pkg.pseudo_homebrew:
            return cls(pkg)

    def __init__(self, *args):
        super(HomebrewManager, self).__init__(*args)

        pkg = self.package

        self.brew = Homebrew(home=pkg.home)

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

    @cached_property
    def untapped_name(self):
        raw_name = self.package.name or self.package.package_name
        return raw_name.split('/')[-1]

    @cached_property
    def tap_name(self):
        raw_name = self.package.name or self.package.package_name
        parts = raw_name.rsplit('/', 1)
        if len(parts) == 2:
            return parts[0]

    def get_next(self, step):
        if step != 'optlink':
            return self

    def init(self):

        pkg = self.package
        pkg.package_name = re.sub(r'^(git\+)?(home)?brew[:+]', '', pkg.url)
        pkg.url = 'brew:' + pkg.package_name

        pkg.name = pkg.name or self.untapped_name

        pkg.package_path = self.brew.cellar

        self.repo = self.brew.repo

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

        # At this point we accept that if there is already something installed
        # in homebrew, we take it. So, we will set our names to that which
        # is already installed.
        self._set_names()

        # Lets fully embrace that.
        if not self.package.id:
            self.package.resolve_existing()

        # If, due to the above, we appear to be installed, then we want to
        # check for all dependencies (like we would after the install process).
        # But since we are very likely to get shortcut due to seemingly being
        # installed, we must check them all now.
        if self.package.installed:
            self._update_dependencies(optional=True, must_exist=True)
        else:
            self._update_dependencies(optional=False, must_exist=False)

    def _update_dependencies(self, optional, must_exist):
        pkg = self.package
        existing = {}
        for dep in pkg.dependencies:
            existing[dep.name] = dep
        cmd = ['deps', '--1']
        if optional:
            cmd.append('--include-optional')
        cmd.append(pkg.package_name)
        for name in self.brew(*cmd, stdout=True).strip().split():
            if name in existing:
                continue
            if must_exist:
                path = os.path.join(self.brew.cellar, name)
                if not os.path.exists(path):
                    continue
            dep = pkg.add_dependency(name=name, url='homebrew:' + name)
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

        # We use the basename for taps (e.g. because ncurses might come out as
        # homebrew/dupes/ncurses, but this heirarchy does not exist in the Cellar).
        pkg.build_name = os.path.join(self.untapped_name,
            'HEAD' if '--HEAD' in pkg.config else self.version
        )
        pkg.build_path = pkg.install_path = os.path.join(self.brew.cellar, pkg.build_name)

        # We set the install_name that we want set for repackaged packages; this
        # should have no effect on actual Homebrew installs.
        pkg.install_name = os.path.join(pkg.package_name,
            'HEAD+%s' % self.revision if '--HEAD' in pkg.config else self.version
        )

        pkg.revision = '%s+%s' % (
            self.version,
            self.revision
        )

    def extract(self):
        pass

    def build(self):

        pkg = self.package

        if not pkg.installed:
            self.brew('install', pkg.package_name, *pkg.config)
            self._set_names()

        self._update_dependencies(optional=True, must_exist=True)

    def install(self):
        pass

    def post_install(self):
        pass
    
    def relocate(self):

        pkg = self.package

        # Standard --relocate and --set-rpath
        relocate_package(pkg)

        if pkg.pseudo_homebrew:

            # --pseudo-homebrew is first handled by the generic.install, which
            # sets the install_path to be in the Homebrew cellar. We finish the
            # job by switching to that version.
            log.info(style_note('Switching Homebrew to %s %s' % (self.untapped_name, self.version)))
            if self.tap_name:
                self.brew.assert_tapped(self.tap_name)
            self.brew('switch', self.untapped_name, self.version)

