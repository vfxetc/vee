import json
import os
import sys

from vee.git import GitRepo
from vee.subproc import call
from vee.utils import  cached_property


class Homebrew(object):

    def __init__(self, path=None, repo=None, home=None):
        self.name = 'linuxbrew' if sys.platform.startswith('linux') else 'homebrew'
        if repo:
            self.repo = repo
        else:
            work_tree = (
                path or
                os.environ.get('VEE_HOMEBREW') or
                home._abs_path('packages', self.name)
            )
            remote_url = 'https://github.com/{}/brew.git'.format(self.name)
            self.repo = GitRepo(work_tree=work_tree, remote_url=remote_url)
        self._info = {}

    @cached_property
    def cellar(self):
        return os.path.join(self.repo.work_tree, 'Cellar')

    def assert_tapped(self, name):
        path = os.path.join(self.repo.work_tree, 'Library', 'Taps', name)
        if not os.path.exists(path):
            self('tap', name)

    def __call__(self, cmd, *args, **kwargs):
        
        brew_head = os.environ.get('VEE_HOMEBREW_COMMIT')
        core_head = os.environ.get('VEE_HOMEBREW_CORE_COMMIT')

        bin_ = os.path.join(self.repo.work_tree, 'bin', 'brew')

        if self.repo.clone_if_not_exists(shallow=not brew_head):
            # Homebrew should be updated the first time, since it has gotten
            # a little more complicated. We call it directly so that
            # it can update itself here, and then our pin will drag it back.
            print "HERE1"
            call((bin_, 'update'))
        
        if brew_head:
            if self.repo.is_shallow:
                self.repo.fetch(shallow=False)
            self.repo.checkout(brew_head)

        if core_head:
            repo = GitRepo(
                os.path.join(self.repo.work_tree, 'Library', 'Taps', 'homebrew', 'homebrew-core'),
                'https://github.com/homebrew/homebrew-core.git',
            )
            repo.clone_if_not_exists(shallow=False)
            if repo.is_shallow:
                repo.fetch(shallow=False)
            repo.checkout(core_head)
        
        # We need to own the homebrew cache so that we can control permissions.
        kwargs['env'] = env = kwargs.get('env', os.environ).copy()
        env.setdefault('HOMEBREW_CACHE', os.path.join(self.repo.work_tree, 'Cache'))
        env.setdefault('HOMEBREW_LOGS', os.path.join(self.repo.work_tree, 'Logs'))

        # Keep our pin.
        if brew_head or core_head:
            env['HOMEBREW_NO_AUTO_UPDATE'] = '1'

        res = call((bin_, cmd) + args, _frame=1, **kwargs)
        if cmd in ('install', 'uninstall'):
            self._info.pop(args[0], None)
        return res

    def info(self, name, force=False):
        if self._info is None:
            self._info = {}
        if force or name not in self._info:
            self._info[name] = json.loads(self('info', '--json=v1', name, stdout=True))[0]
        return self._info[name]
