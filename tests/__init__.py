from cStringIO import StringIO
import atexit
import fnmatch
import os
import random
import re
import shutil
import SimpleHTTPServer
import SocketServer
import subprocess
import sys
import tarfile
import urllib2

from unittest import TestCase as _TestCase
from vee.commands.main import main as _main
from vee.git import GitRepo

# These may depend on the above paths.
from .mock.http import setup_mock_http, mock_url
from .mock.package import MockPackage


tests_dir = os.path.abspath(os.path.join(__file__, '..'))
root_dir = os.path.dirname(tests_dir)
sandbox_dir = os.path.join(tests_dir, 'sandbox')



# Clear out the sandbox.
if os.path.exists(sandbox_dir):
    shutil.rmtree(sandbox_dir)
os.makedirs(sandbox_dir)

# Setup mock HTTP server.
setup_mock_http(sandbox_dir)


def vee(args, environ=None):
    full_environ = os.environ.copy()
    full_environ.update(environ or {})
    full_environ['VEE'] = os.path.join(sandbox_dir, 'vee')
    return _main(args, environ=full_environ)


def sandbox(*args):
    return os.path.join(sandbox_dir, *args)


class TestCase(_TestCase):

    def assertExists(self, path, *args):
        self.assertTrue(os.path.exists(path), *args)



