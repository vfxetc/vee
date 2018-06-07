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
from vee.semver import Version, VersionExpr
from vee.pipeline.http import download

PYPI_URL_PATTERN = 'https://pypi.org/pypi/%s/json'


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
        self.name = re.sub(r'^pypi[:+]', '', pkg.url).lower()
        pkg.url = 'pypi:' + self.name

    def _meta(self):
        pkg = self.package
        path = pkg.home._abs_path('packages', 'pypi', self.name, 'meta.json')
        if not os.path.exists(path):
            log.info(style_note('Looking up %s on PyPI' % self.name))
            url = PYPI_URL_PATTERN % self.name
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

        if pkg.revision:
            expr = VersionExpr(pkg.revision)
            matching_releases = [(v, rs) for v, rs in all_releases if expr.eval(v)]
            log.debug('%s matched %s' % (expr, ','.join(str(v) for v, _ in matching_releases) or 'none'))
        else:
            matching_releases = all_releases

        for version, releases in matching_releases:
            release = next((r for r in releases if r['packagetype'] == 'sdist'), None)
            if release:
                break
        else:
            raise ValueError('no sdist %s %s on the PyPI;' % (self.name, expr if pkg.revision else '(any)'))

        pkg.revision = str(version)
        
        if release.get('md5_digest'):
            pkg.checksum = 'md5:%s' % release['md5_digest']

        pkg.package_name = os.path.join(self.name, os.path.basename(release['url']))
        pkg._assert_paths(package=True)

        if os.path.exists(pkg.package_path):
            log.info(style_note('Already downloaded', release['url']))
            return
        log.info(style_note('Downloading', release['url']))
        download(release['url'], pkg.package_path)


