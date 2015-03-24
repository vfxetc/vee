import datetime
import os
import urllib2
import urlparse
import re
import shutil
import json

from vee.cli import style, style_note
from vee.packages.base import BasePackage
from vee.utils import makedirs
from vee import log


class PyPiPackage(BasePackage):

    type = 'pypi'
    
    factory_priority = 1000

    @classmethod
    def factory(cls, req, *args):
        if re.match(r'^pypi[:+]', req.url):
            return cls(req, *args)

    def __init__(self, *args, **kwargs):
        super(PyPiPackage, self).__init__(*args, **kwargs)
        self.package_name = re.sub(r'^pypi[:+]', '', self.url)
        self.url = 'pypi:' + self.package_name

    @property
    def _derived_package_name(self):
        split = urlparse.urlsplit(self.url)
        return os.path.join(
            split.netloc,
            split.path.strip('/'),
        )

    def _meta(self):
        path = self.home._abs_path('packages', 'pypi', self.name.lower(), 'meta.json')
        if not os.path.exists(path):
            log.info(style_note('Looking up %s on PyPI' % self.name))
            url = 'https://pypi.python.org/pypi/%s/json' % self.name.lower()
            res = urllib2.urlopen(url)
            makedirs(os.path.dirname(path))
            with open(path, 'wb') as fh:
                fh.write(res.read())
        return json.load(open(path, 'rb'))

    def fetch(self):

        meta = self._meta()

        self.revision, releases = sorted(meta['releases'].items())[-1]
        release = next((r for r in releases if r['packagetype'] == 'sdist'), None)
        if not release:
            raise ValueError('no sdist %s on the PyPI' % self.name)

        self.package_name = os.path.join(self.name, os.path.basename(release['url']))

        self._assert_paths(package=True)

        if os.path.exists(self.package_path):
            log.info(style('Already downloaded.', 'blue', bold=True))
            return

        makedirs(os.path.dirname(self.package_path))

        temp = self.package_path + '.downloading'

        log.info(style('Downloading', 'blue', bold=True), style(self.url, bold=True))

        src_fh = None
        dst_fh = None
        try:
            src_fh = urllib2.urlopen(release['url'])
            dst_fh = open(temp, 'wb')
            # TODO: Indicate progress.
            for chunk in iter(lambda: src_fh.read(16384), ''):
                dst_fh.write(chunk)
        finally:
            if src_fh:
                src_fh.close()
            if dst_fh:
                dst_fh.close()

        shutil.move(temp, self.package_path)


