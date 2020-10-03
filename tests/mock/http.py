from io import BytesIO, StringIO
import fnmatch
import json
import os
import re
import tarfile
import threading
import random

from six.moves.socketserver import TCPServer
from six.moves.BaseHTTPServer import BaseHTTPRequestHandler

from vee.pipeline import pypi


# Global state is gross.
_host = '127.0.0.1'
_port = random.randrange(1025, 65535)
_netloc = '{}:{}'.format(_host, _port)
_root = None
_thread = None


def mock_url(path):
    rel_path = os.path.relpath(os.path.join(_root, path), _root)
    if rel_path.startswith('.'):
        raise ValueError('not a mock http path: %r' % path)
    return 'http://%s/%s' % (_netloc, rel_path.strip('/'))


def setup_mock_http(root):

    global _root, _thread
    if _root:
        raise RuntimeError('mock http already setup')

    _thread = threading.Thread(target=serve)
    _thread.daemon = True
    _thread.start()

    pypi.PYPI_URL_PATTERN = 'http://{}/pypi/%s/json'.format(_netloc)

    _root = root


def serve():
    httpd = TCPServer((_host, _port), MockHTTPHandler)
    httpd.serve_forever()


class MockHTTPHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        # self.close_connection = True
        
        url_path = self.path

        # Mock PyPI.
        m = re.match(r'/pypi/(.+)/json', url_path)
        if m:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({
                'releases': {
                    '1.0.0': [{
                        'packagetype': 'sdist',
                        'url': 'http://%s/packages/%s.tgz' % (_netloc, m.group(1))
                    }],
                },  
            }).encode())
            return

        # Files which exist.
        path = os.path.join(_root, url_path.strip('/'))
        if os.path.exists(path):
            content = open(path, 'rb').read()
            self.send_response(200)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        # Create tarballs on the fly.
        basename, ext = os.path.splitext(path)
        if os.path.exists(basename) and ext == '.tgz':

            fh = BytesIO()
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
            content = fh.getvalue()

            self.send_response(200)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_response(404)
        self.end_headers()


