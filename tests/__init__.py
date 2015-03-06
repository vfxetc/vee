import os
import re
import shutil
import sys
import subprocess

from unittest import TestCase as _TestCase
from vee.commands.main import main as _main
from vee.git import GitRepo
from vee.home import Home

from .mock.http import setup_mock_http, mock_url
from .mock.package import MockPackage
from .mock.repo import MockRepo


tests_dir = os.path.abspath(os.path.join(__file__, '..'))
root_dir = os.path.dirname(tests_dir)
sandbox_dir = os.path.join(root_dir, 'sandbox')



# Clear out the sandbox.
if os.path.exists(sandbox_dir):
    for name in os.listdir(sandbox_dir):
        # Leave Homebrew between tests.
        if name == 'Homebrew':
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

# Setup root for inheriting.
VEE = os.path.join(sandbox_dir, 'vee')
_environ_diff = {
    'VEE': VEE,
    # 'VEE_DEV': os.path.join(VEE, 'dev'),
    # 'VEE_REPO': 'sandbox',
    'VEE_HOMEBREW': sandbox('Homebrew'),
    'PATH': '%s:%s' % (os.path.join(root_dir, 'bin'), os.environ['PATH']),
}
os.environ.update(_environ_diff)

# Setup mock HTTP server.
setup_mock_http(sandbox_dir)

home = Home(VEE)


def vee(args, environ=None):
    full_environ = os.environ.copy()
    full_environ.update(environ or {})
    full_environ.update(_environ_diff)
    return _main(args, environ=full_environ)




class TestCase(_TestCase):

    def class_sandbox(self, *args):
        return sandbox('homes', self.__class__.__name__, 'class', *args)

    def sandbox(self, *args):
        return self.class_sandbox(self._testMethodName, *args)

    def class_home(self):
        return Home(self.class_sandbox())

    def home(self):
        return Home(self.sandbox())

    def repo(self):
        return MockRepo('%s/%s' % (self.__class__.__name__, self._testMethodName))

    def package(self, name='foo', type=None, defaults=None):
        return MockPackage(name, type or 'c_configure_make_install', defaults, os.path.join(self.__class__.__name__, self._testMethodName, name))

    def assertExists(self, path, *args):
        args = args or [path + ' does not exist']
        self.assertTrue(os.path.exists(path), *args)



