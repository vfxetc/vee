import datetime
import json
import os
import re
import shutil
import subprocess
import sys

from vee import log
from vee.cli import style, style_note
from vee.pipeline.base import PipelineStep
from vee.pipeline.http import download
from vee.python import get_default_python
from vee.semver import Version, VersionExpr
from vee.utils import makedirs, http_request


PYPI_URL_PATTERN = 'https://pypi.org/pypi/%s/json'


_supported_tags = []
def get_supported_tags():
    if not _supported_tags:
        out = subprocess.check_output([
            get_default_python().executable,
            '-sc',
            '''
import json
import packaging.tags
print(json.dumps([(t.interpreter, t.abi, t.platform) for t in packaging.tags.sys_tags()]))
''']).decode().strip()
        _supported_tags.extend(tuple(x) for x in json.loads(out))

    return _supported_tags


class PyPiTransport(PipelineStep):
    
    factory_priority = 1000

    @classmethod
    def factory(cls, step, pkg):
        if step == 'init' and re.match(r'^pypi[:+]', pkg.url):
            return cls()

    def get_next(self, step, pkg):
        if step in ('fetch', ):
            return self

    def init(self, pkg):
        self.name = re.sub(r'^pypi[:+]', '', pkg.url).lower()
        pkg.url = 'pypi:' + self.name

    def _get_meta(self, pkg):
        
        path = pkg.home._abs_path('packages', 'pypi', self.name, 'meta.json')

        log.info(style_note('Looking up %s on PyPI' % self.name))
        url = PYPI_URL_PATTERN % self.name
        res = http_request('GET', url)
        body = res.data
        meta = json.loads(body)

        return meta

    def fetch(self, pkg):

        meta = self._get_meta(pkg)

        all_releases = [(Version(v), rs) for v, rs in meta['releases'].items()]
        all_releases.sort(reverse=True)

        if not all_releases:
            raise ValueError('no releases of {} (any version) on the PyPI'.format(self.name))

        if pkg.version:
            matching_releases = [(v, rs) for v, rs in all_releases if pkg.version == v]
            if not matching_releases:
                raise ValueError('no releases of {} {} on the PyPI'.format(self.name, pkg.version))

        else:
            matching_releases = all_releases

        supported_tags = get_supported_tags()

        usable_releases = []
        for version, releases in matching_releases:

            for release in releases:

                if release['packagetype'] == 'sdist':
                    usable_releases.append((version, 0, release))
                    continue

                elif release['packagetype'] == 'bdist_wheel':
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
            raise ValueError('no usable release of %s %s on the PyPI;' % (self.name, expr if pkg.version else '(any version)'))
        usable_releases.sort(key=lambda x: x[:2])

        version, _, release = usable_releases[-1]

        pkg.version = str(version)
        
        if release.get('md5_digest'):
            pkg.checksum = 'md5:%s' % release['md5_digest']

        pkg.package_name = os.path.join(self.name, os.path.basename(release['url']))
        pkg._assert_paths(package=True)

        if os.path.exists(pkg.package_path):
            log.info(style_note('Already downloaded', release['url']))
            return
        
        log.info(style_note('Downloading', release['url']))
        download(release['url'], pkg.package_path)


