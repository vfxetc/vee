import json
import os
import re
import shlex
import sys

from vee.cli import style
from vee.packages.git import GitPackage
from vee.subproc import call
from vee.utils import makedirs, cached_property
from vee import log


class HomebrewPackage(GitPackage):

    type = 'homebrew'

    factory_priority = 1000

    @classmethod
    def factory(cls, req, *args):
        if re.match(r'^homebrew[:+]', req.url):
            return cls(req, *args)

    def __init__(self, *args, **kwargs):
        super(HomebrewPackage, self).__init__(*args, **kwargs)
        self.package_name = re.sub(r'^(git\+)?homebrew[:+]', '', self.url)
        self.url = 'homebrew:' + self.package_name

        if self.install_name:
            raise ValueError("Can't set install_name on Homebrew packages")

    @cached_property
    def _name_for_platform(self):
        return 'linuxbrew' if sys.platform.startswith('linux') else 'homebrew'

    @cached_property
    def _git_remote_url(self):
        return 'https://github.com/Homebrew/%s.git' % self._name_for_platform

    @cached_property
    def _brew_bin(self):
        return os.path.join(self.package_path, 'bin', 'brew')

    def _brew(self, *cmd, **kwargs):
        self.repo.clone_if_not_exists()
        return call((self._brew_bin, ) + cmd, env=self.fresh_environ(), **kwargs)

    _cached_brew_info = None

    def _brew_info(self, name=None, force=False):

        if self._cached_brew_info is None:
            self._cached_brew_info = {}

        name = name or self.package_name
        if force or name not in self._cached_brew_info:
            self._cached_brew_info[name] = json.loads(self._brew('info', '--json=v1', name, stdout=True))[0]

        return self._cached_brew_info[name]

    def _set_names(self, package=False, build=False, install=False):
        if build or install and not self.build_name:
            if '--HEAD' in self.config:
                self.build_name = '%s/HEAD' % self.name
            else:
                self.build_name = self.install_name_from_info()
        if install and not self.install_name:
            self.install_name = self.build_name
            log.debug('install_name for %s set to %r' % (self.name, self.install_name))

    def install_name_from_info(self, name=None, info=None):
        name = name or self.package_name
        info = info or self._brew_info(name)
        if not info:
            raise ValueError('no homebrew package %s' % name)
        return '%s/%s' % (info['name'], info['linked_keg'] or (
            info['installed'][-1]['version']
            if info['installed']
            else info['versions']['stable']
        ))

    @property
    def package_path(self):
        override = os.environ.get('VEE_HOMEBREW')
        if override:
            return override
        else:
            return self.home._abs_path('packages', self._name_for_platform)

    @property
    def build_path(self):
        return self.install_name and os.path.join(self.package_path, 'Cellar', self.install_name)

    install_path = build_path

    def extract(self):
        # Disable BasePackage.extract().
        pass

    def build(self):
        if self.installed:
            log.warning(self.package_name + ' is already built', 'black')
            return
        self._brew('install', self.package_name, *self.config)

        # Need to force a new installed version number.
        self._brew_info(force=True)

    def install(self):
        # Disable BasePackage.install().
        pass

    def link(self, env, force=None):
        
        # Be careful with this, since it is a full replacement of the base link
        # method.
        
        self._assert_paths(install=True)
        frozen = self.freeze()
        if not force:
            self._assert_unlinked(env, frozen)

        # We want to link in all dependencies as well.
        for name in self._brew('deps', '-n', self.package_name, stdout=True).strip().split():
            path = os.path.join(self.package_path, 'Cellar', self.install_name_from_info(name))
            if os.path.exists(path):
                log.info(style('Linking ', 'blue', bold=True) + style('homebrew:%s (homebrew:%s dependency)' % (name, self.package_name), bold=True))
                env.link_directory(path)

        log.info(style('Linking ', 'blue', bold=True) + style(str(frozen), bold=True))
        env.link_directory(self.install_path)
        self._record_link(env)
