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

        if req.get_host() != 'localhost.mock':
            return urllib2.HTTPHandler.http_open(self, req)

        # Files which exist.
        asset_path = os.path.join(assets_dir, req.get_selector().strip('/'))
        if os.path.exists(asset_path):
            res = urllib2.addinfourl(open(asset_path), 'HEADERS', req.get_full_url())
            res.code = 200
            res.msg = 'OK'
            return res

        # Create tarballs on the fly.
        asset_base, ext = os.path.splitext(asset_path)
        if os.path.exists(asset_base) and ext == '.tgz':

            fh = StringIO()
            tgz = tarfile.open(fileobj=fh, mode='w:gz')

            ignore_path = os.path.join(asset_base, 'mockignore')
            if os.path.exists(ignore_path):
                patterns = [x.strip() for x in open(ignore_path)] + ['mockignore']
                pattern = re.compile('|'.join(fnmatch.translate(x) for x in patterns if x))

            for dir_path, dir_names, file_names in os.walk(asset_base):
                for file_name in file_names:
                    if pattern.match(file_name):
                        continue
                    file_path = os.path.join(dir_path, file_name)
                    tgz.add(file_path, os.path.relpath(file_path, asset_base))

            tgz.close()
            fh.seek(0)

            res = urllib2.addinfourl(fh, 'HEADERS', req.get_full_url())
            res.code = 200
            res.msg = 'OK'
            return res

        res = urllib2.addinfourl(StringIO('404 NOT FOUND'), 'HEADERS', req.get_full_url())
        res.code = 404
        res.msg = 'NOT FOUND'
        return res

urllib2.install_opener(urllib2.build_opener(MockHTTPHandler))

def asset_url(path):
    rel_path = os.path.relpath(os.path.abspath(os.path.join(assets_dir, path)), assets_dir)
    if rel_path.startswith('.'):
        raise ValueError('not an asset path: %r' % path)
    return 'http://localhost.mock/' + rel_path.strip('/')


if os.path.exists(sandbox_dir):
    shutil.rmtree(sandbox_dir)
os.makedirs(sandbox_dir)

def sandbox(*args):
    return os.path.join(sandbox_dir, *args)


