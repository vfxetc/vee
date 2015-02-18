from cStringIO import StringIO
import atexit
import os
import random
import shutil
import SimpleHTTPServer
import SocketServer
import subprocess
import sys
import urllib2

from unittest import TestCase
from vee.commands.main import main as _main


tests_dir = os.path.abspath(os.path.join(__file__, '..'))
root_dir = os.path.dirname(tests_dir)
assets_dir = os.path.join(tests_dir, 'assets') 
sandbox_dir = os.path.join(tests_dir, 'sandbox')


def vee(args, environ=None):

    full_environ = os.environ.copy()
    full_environ.update(environ or {})
    full_environ['VEE'] = sandbox_dir

    return _main(args, environ=full_environ)


class MockHTTPHandler(urllib2.HTTPHandler):

    def http_open(self, req):
        if req.get_host() == 'assets.vee.mock':
            asset_path = os.path.join(assets_dir, req.get_selector().strip('/'))
            if os.path.exists(asset_path):
                res = urllib2.addinfourl(open(asset_path), 'HEADERS', req.get_full_url())
                res.code = 200
                res.msg = 'OK'
                return res
            else:
                res = urllib2.addinfourl(StringIO('404 NOT FOUND'), 'HEADERS', req.get_full_url())
                res.code = 404
                res.msg = 'NOT FOUND'
                return res
        return urllib2.HTTPHandler.http_open(self, req)

urllib2.install_opener(urllib2.build_opener(MockHTTPHandler))

def asset_url(path):
    rel_path = os.path.relpath(os.path.abspath(os.path.join(assets_dir, path)), assets_dir)
    if rel_path.startswith('.'):
        raise ValueError('not an asset path: %r' % path)
    return 'http://assets.vee.mock/' + rel_path.strip('/')


if os.path.exists(sandbox_dir):
    shutil.rmtree(sandbox_dir)
os.makedirs(sandbox_dir)

def sandbox(*args):
    return os.path.join(sandbox_dir, *args)


