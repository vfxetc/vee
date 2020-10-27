from textwrap import dedent
import os
import re
import shutil
import subprocess
import sys

try:
    from unittest.case import SkipTest as _Skip
except ImportError:
    _Skip = None

from unittest import TestCase as _TestCase

from vee import log
from vee.cli import strip_ansi
from vee.commands.main import main as _main
from vee.git import GitRepo
from vee.home import Home
from vee.python import get_default_python
from vee.subproc import call
from vee.utils import makedirs

from .mock.http import setup_mock_http, mock_url
from .mock.package import MockPackage
from .mock.repo import MockRepo


# Uncomment this if you want the logs.
# log.root.propagate = True


tests_dir = os.path.abspath(os.path.join(__file__, '..'))
root_dir = os.path.dirname(tests_dir)
sandbox_dir = os.path.join(root_dir, 'sandbox')

is_travis = bool(os.environ.get('TRAVIS'))


# Clear out the sandbox.
if os.path.exists(sandbox_dir):
    for name in os.listdir(sandbox_dir):
        # Leave Homebrew between tests.
        if name in ('Homebrew', 'Vendor'):
            continue
        path = os.path.join(sandbox_dir, name)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.unlink(path)
else:
    os.makedirs(sandbox_dir)

def sandbox(*args):
    return os.path.join(sandbox_dir, *args)

# Move into the sandbox.
os.chdir(sandbox_dir)

# Clear out any VEE* envvars as this tends to mess up testing.
for k in os.environ.keys():
    if k.startswith('VEE'):
        del os.environ[k]

# Setup root for inheriting.
VEE = os.path.join(sandbox_dir, 'vee')
_environ_diff = {
    'VEE': VEE,
    # 'VEE_DEV': os.path.join(VEE, 'dev'),
    # 'VEE_REPO': 'sandbox',
    'VEE_HOMEBREW': sandbox('Homebrew'),
    'VEE_VENDOR': os.path.join(sandbox_dir, 'Vendor'),
    'PATH': '%s:%s' % (os.path.join(root_dir, 'bin'), os.environ['PATH']),
}
os.environ.update(_environ_diff)


default_python = get_default_python()


# Setup mock HTTP server.
setup_mock_http(sandbox_dir)

home = Home(VEE)
home.init()

def vee(args, environ=None, check=True, stdout=False):
    full_environ = os.environ.copy()
    full_environ.update(environ or {})
    full_environ.update(_environ_diff)
    log.debug('$ vee ' + ' '.join(args), name='vee.tests')
    if stdout:
        cmd = ['vee']
        cmd.extend(args)
        return subprocess.check_output(cmd, env=environ)
    res = _main(args, environ=full_environ)
    if check and res:
        raise ValueError('return code %d' % res)
    return res


def skip():
    if _Skip:
        raise _Skip()
    else:
        return


class TestCase(_TestCase):

    @property
    def test_name(self):
        return self.__class__.__name__ + '/' + self._testMethodName

    def class_sandbox(self, *args):
        return sandbox('homes', self.__class__.__name__, '__class__', *args)

    def sandbox(self, *args):
        return self.class_sandbox(self._testMethodName, *args)

    def class_home(self, init=None):
        return self.home(self.class_sandbox(), init)

    def home(self, path=None, init=None):
        home = Home(path or self.sandbox())
        makedirs(os.path.dirname(home.root))
        if init is None:
            init = not home.db.exists
        if init:
            home.init(create_parents=True)
        return home

    def repo(self):
        return MockRepo('%s/%s' % (self.__class__.__name__, self._testMethodName))

    def package(self, name='foo', type=None, defaults=None):
        return MockPackage(name, type or 'c_configure_make_install', defaults, os.path.join(self.__class__.__name__, self._testMethodName, name))

    def assertExists(self, path, *args):
        args = args or [path + ' does not exist']
        self.assertTrue(os.path.exists(path), *args)



