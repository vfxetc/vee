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


class Homebrew(GitTransport):

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

        pkg.package_path = os.environ.get('VEE_HOMEBREW') or pkg.home._abs_path('packages', self._name_for_platform)

        if pkg.install_name:
            raise ValueError("Can't set install_name on Homebrew packages")

        # We run the super init after since it will create a GitRepo object
        # using the package_path.
        super(Homebrew, self).__init__(pkg, *args, **kwargs)

    @cached_property
    def _name_for_platform(self):
        return 'linuxbrew' if sys.platform.startswith('linux') else 'homebrew'

    @cached_property
    def _git_remote_url(self):
        return 'https://github.com/Homebrew/%s.git' % self._name_for_platform

    @cached_property
    def _brew_bin(self):
        return os.path.join(self.package.package_path, 'bin', 'brew')

    def _brew(self, *cmd, **kwargs):
        self.repo.clone_if_not_exists()
        return call((self._brew_bin, ) + cmd, env=self.package.fresh_environ(), **kwargs)

    _cached_brew_info = None

    def _brew_info(self, name=None, force=False):

        if self._cached_brew_info is None:
            self._cached_brew_info = {}

        name = name or self.package.package_name
        if force or name not in self._cached_brew_info:
            self._cached_brew_info[name] = json.loads(self._brew('info', '--json=v1', name, stdout=True))[0]

        return self._cached_brew_info[name]

    # TODO: look this back up.
    def _set_names(self, package=False, build=False, install=False):
        pkg = self.package

        if '--HEAD' in pkg.config:
            pkg.build_name = pkg.install_name = '%s/HEAD' % pkg.name
        else:
            pkg.build_name = pkg.install_name = self.install_name_from_info()

        pkg.build_path = pkg.install_path = os.path.join(pkg.package_path, 'Cellar', pkg.install_name)

    def install_name_from_info(self, name=None, info=None):
        name = name or self.package.package_name
        info = info or self._brew_info(name)
        if not info:
            raise ValueError('no homebrew package %s' % name)
        return '%s/%s' % (info['name'], info['linked_keg'] or (
            info['installed'][-1]['version']
            if info['installed']
            else info['versions']['stable']
        ))

    def inspect(self):
        # Do nothing.
        pass

    def extract(self):
        # Do nothing.
        pass

    def build(self):
        pkg = self.package
        if pkg.installed:
            log.warning(pkg.package_name + ' is already built', 'black')
            return
        self._brew('install', pkg.package_name, *pkg.config)

        # Need to force a new installed version number.
        self._brew_info(force=True)
        self._set_names()

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
        for name in self._brew('deps', '-n', self.package_name, stdout=True).strip().split():
            path = os.path.join(self.package_path, 'Cellar', self.install_name_from_info(name))
            if os.path.exists(path):
                log.info(style('Linking ', 'blue', bold=True) + style('homebrew:%s (homebrew:%s dependency)' % (name, self.package_name), bold=True))
                env.link_directory(path)

        log.info(style('Linking ', 'blue', bold=True) + style(str(frozen), bold=True))
        env.link_directory(self.install_path)
        self._record_link(env)
