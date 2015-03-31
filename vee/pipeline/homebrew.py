import json
import os
import re
import shlex
import sys

from vee.cli import style
from vee.pipeline.git import GitTransport
from vee.subproc import call
from vee.utils import makedirs, cached_property
from vee import log
from vee.homebrew import Homebrew


class HomebrewManager(GitTransport):

    type = 'homebrew'

    factory_priority = 1000

    @classmethod
    def factory(cls, step, pkg, *args):
        if re.match(r'^homebrew[:+]', pkg.url):
            return cls(pkg, *args)

    def get_successor(self, step):
        return self

    def __init__(self, pkg, *args, **kwargs):

        pkg.package_name = re.sub(r'^(git\+)?homebrew[:+]', '', pkg.url)
        pkg.url = 'homebrew:' + pkg.package_name

        self.brew = Homebrew(home=pkg.home)
        pkg.package_path = self.brew.cellar

        # We run the super init after since we want to pass it a repo.
        kwargs['_repo'] = self.brew.repo
        super(HomebrewManager, self).__init__(pkg, *args, **kwargs)

    def set_pkg_names(self, package=False, build=False, install=False):
        pkg = self.package
        if '--HEAD' in pkg.config:
            pkg.build_name = pkg.install_name = '%s/HEAD' % pkg.package_name
        else:
            pkg.build_name = pkg.install_name = self.brew.install_name_from_info(pkg.name)
        pkg.build_path = pkg.install_path = os.path.join(self.brew.cellar, pkg.install_name)

    def inspect(self):
        # Do nothing.
        # TODO: Determine deps here.
        pass

    def extract(self):
        # Do nothing.
        pass

    def build(self):
        pkg = self.package
        if pkg.installed:
            log.warning(pkg.package_name + ' is already built', 'black')
            return
        self.brew('install', pkg.package_name, *pkg.config)
        self.set_pkg_names()

    def install(self):
        # Do nothing.
        pass

    def link(self, env, force=None):
        
        # Be careful with this, since it is a full replacement of the base link
        # method.
        
        self._assert_paths(install=True)
        frozen = self.freeze()
        if not force:
            self._assert_unlinked(env, frozen)

        # We want to link in all dependencies as well.
        for name in self.brew('deps', '-n', self.package_name, stdout=True).strip().split():
            path = os.path.join(self.package_path, 'Cellar', self.install_name_from_info(name))
            if os.path.exists(path):
                log.info(style('Linking ', 'blue', bold=True) + style('homebrew:%s (homebrew:%s dependency)' % (name, self.package_name), bold=True))
                env.link_directory(path)

        log.info(style('Linking ', 'blue', bold=True) + style(str(frozen), bold=True))
        env.link_directory(self.install_path)
        self._record_link(env)
