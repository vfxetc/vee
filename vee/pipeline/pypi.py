import datetime
import json
import os
import re
import shutil
import sys

from vee import log
from vee.cli import style, style_note
from vee.pipeline.base import PipelineStep
from vee.pipeline.http import download
from vee.semver import Version, VersionExpr
from vee.utils import makedirs, http_request

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

        log.info(style_note('Looking up %s on PyPI' % self.name))
        url = PYPI_URL_PATTERN % self.name
        res = http_request('GET', url)
        body = res.data
        meta = json.loads(body)

        return meta

    def fetch(self):

        pkg = self.package
        meta = self._meta()

        all_releases = [(Version(v), rs) for v, rs in meta['releases'].items()]
        all_releases.sort(reverse=True)

        if not all_releases:
            raise ValueError('no releases of {} (any version) on the PyPI'.format(self.name))

        if pkg.revision:
            expr = VersionExpr(pkg.revision)
            matching_releases = [(v, rs) for v, rs in all_releases if expr.eval(v)]
            log.debug('%s matched %s' % (expr, ','.join(str(v) for v, _ in matching_releases) or 'none'))

            if not matching_releases:
                raise ValueError('no releases of {} {} on the PyPI'.format(self.name, expr))

        else:
            matching_releases = all_releases

        # We delay the import just in case the bootstrap is borked.
        import packaging.tags
        supported_tags = [(t.interpreter, t.abi, t.platform) for t in packaging.tags.sys_tags()]

        usable_releases = []
        for version, releases in matching_releases:

            for release in releases:

                if release['packagetype'] == 'sdist':
                    usable_releases.append((version, 0, release))
                    continue

                if release['packagetype'] == 'bdist_wheel':
                    m = re.match(r'^(.+)-([^-]+)-([^-]+)-([^-]+)-([^-]+)\.whl$', release['filename'])
                    if not m:
                        log.warning("Could not parse wheel filename: {}".format(release['filename']))
                    
                    name, version_tag, python_tag, abi_tag, platform_tags = m.groups()

                    # Platform tags can have multiple seperated by dots.
                    for platform_tag in platform_tags.split('.'):
                        tags = (python_tag, abi_tag, platform_tag)
                        if tags in supported_tags:
                            break
                    else:
                        continue

                    usable_releases.append((version, 1, release))

        if not usable_releases:
            raise ValueError('no usable release of %s %s on the PyPI;' % (self.name, expr if pkg.revision else '(any version)'))
        usable_releases.sort()

        version, _, release = usable_releases[-1]

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


