import datetime
import os
import urllib2
import urlparse
import re
import shutil
import json

from vee.cli import style, style_note
from vee.pipeline.base import PipelineStep
from vee.utils import makedirs
from vee import log
from vee.semver import Version
from vee.pipeline.http import download

PYPI_URL_PATTERN = 'https://pypi.python.org/pypi/%s/json'


class PyPiTransport(PipelineStep):
    
    factory_priority = 1000

    @classmethod
    def factory(cls, step, pkg):
        if step == 'init' and re.match(r'^pypi[:+]', pkg.url):
            return cls(pkg)

    def get_next(self, step):
        if step in ('fetch', ):
            return self

    def init(self):
        pkg = self.package
        pkg.url = 'pypi:' + re.sub(r'^pypi[:+]', '', pkg.url)

    def _meta(self):
        pkg = self.package
        path = pkg.home._abs_path('packages', 'pypi', pkg.name.lower(), 'meta.json')
        if not os.path.exists(path):
            log.info(style_note('Looking up %s on PyPI' % pkg.name))
            url = PYPI_URL_PATTERN % pkg.name.lower()
            res = urllib2.urlopen(url)
            makedirs(os.path.dirname(path))
            with open(path, 'wb') as fh:
                fh.write(res.read())
        return json.load(open(path, 'rb'))

    def fetch(self):

        pkg = self.package
        meta = self._meta()

        all_releases = [(Version(v), rs) for v, rs in meta['releases'].iteritems()]
        all_releases.sort(reverse=True)

        for version, releases in all_releases:
            release = next((r for r in releases if r['packagetype'] == 'sdist'), None)
            if release:
                break
        else:
            raise ValueError('no sdist %s on the PyPI' % self.name)

        pkg.revision = str(version)

        pkg.package_name = os.path.join(pkg.name, os.path.basename(release['url']))
        pkg._assert_paths(package=True)

        if os.path.exists(pkg.package_path):
            log.info(style_note('Already downloaded', release['url']))
            return
        log.info(style_note('Downloading', release['url']))
        download(release['url'], pkg.package_path)


