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


# For nose to capture stderr.
os.dup2(1, 2)


tests_dir = os.path.abspath(os.path.join(__file__, '..'))
root_dir = os.path.dirname(tests_dir)
sandbox_dir = os.path.join(tests_dir, 'sandbox')
VEE = os.path.join(sandbox_dir, 'vee')



# Clear out the sandbox.
if os.path.exists(sandbox_dir):
    shutil.rmtree(sandbox_dir)
os.makedirs(sandbox_dir)

# Setup mock HTTP server.
setup_mock_http(sandbox_dir)

home = Home(VEE)
os.chdir(sandbox_dir)


def vee(args, environ=None):
    full_environ = os.environ.copy()
    full_environ.update(environ or {})
    full_environ['VEE'] = VEE
    return _main(args, environ=full_environ)


def sandbox(*args):
    return os.path.join(sandbox_dir, *args)


class TestCase(_TestCase):

    def class_home(self):
        return Home(sandbox('homes', self.__class__.__name__, 'class'))

    def home(self):
        return Home(sandbox('homes', self.__class__.__name__, self._testMethodName))

    def repo(self):
        return MockRepo('%s/%s' % (self.__class__.__name__, self._testMethodName))

    def package(self, name='foo', type=None, defaults=None):
        return MockPackage(name, type or 'c_configure_make_install', defaults, os.path.join(self.__class__.__name__, self._testMethodName, name))

    def assertExists(self, path, *args):
        args = args or [path + ' does not exist']
        self.assertTrue(os.path.exists(path), *args)



