from io import StringIO
import fnmatch
import os
import re
import tarfile
import urllib.request
import json

from vee.pipeline import pypi


# Global state is gross.
_host = 'vee.localhost.mock'
_root = None


def setup_mock_http(root):
    global _root
    if _root:
        raise RuntimeError('mock http already setup')
    _root = root
    urllib.request.install_opener(urllib.request.build_opener(MockHTTPHandler))
    pypi.PYPI_URL_PATTERN = 'http://%s/pypi/%%s/json' % _host


def mock_url(path):
    rel_path = os.path.relpath(os.path.join(_root, path), _root)
    if rel_path.startswith('.'):
        raise ValueError('not a mock http path: %r' % path)
    return 'http://%s/%s' % (_host, rel_path.strip('/'))


class MockHTTPHandler(urllib.request.HTTPHandler):

    def http_open(self, req):

        if req.get_host() != _host:
            return urllib.request.HTTPHandler.http_open(self, req)
        url_path = req.get_selector()

        # PyPI
        m = re.match(r'/pypi/(.+)/json', url_path)
        if m:
            res = urllib.request.addinfourl(StringIO(json.dumps({
                'releases': {
                    '1.0.0': [{
                        'packagetype': 'sdist',
                        'url': 'http://%s/packages/%s.tgz' % (_host, m.group(1))
                    }],
                },  
            })), 'HEADERS', req.get_full_url())
            res.code = 200
            res.msg = 'OK'
            return res

        # Files which exist.
        path = os.path.join(_root, url_path.strip('/'))
        if os.path.exists(path):
            res = urllib.request.addinfourl(open(path), 'HEADERS', req.get_full_url())
            res.code = 200
            res.msg = 'OK'
            return res

        # Create tarballs on the fly.
        basename, ext = os.path.splitext(path)
        if os.path.exists(basename) and ext == '.tgz':

            fh = StringIO()
            tgz = tarfile.open(fileobj=fh, mode='w:gz')

            ignore_path = os.path.join(basename, 'mockignore')
            if os.path.exists(ignore_path):
                patterns = [x.strip() for x in open(ignore_path)] + ['mockignore']
                pattern = re.compile('|'.join(fnmatch.translate(x) for x in patterns if x))
            else:
                pattern = None

            for dir_path, dir_names, file_names in os.walk(basename):
                for file_name in file_names:
                    if pattern and pattern.match(file_name):
                        continue
                    file_path = os.path.join(dir_path, file_name)
                    tgz.add(file_path, os.path.relpath(file_path, basename))

            tgz.close()
            fh.seek(0)

            res = urllib.request.addinfourl(fh, 'HEADERS', req.get_full_url())
            res.code = 200
            res.msg = 'OK'
            return res

        res = urllib.request.addinfourl(StringIO('404 NOT FOUND'), 'HEADERS', req.get_full_url())
        res.code = 404
        res.msg = 'NOT FOUND'
        return res

