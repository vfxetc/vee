import datetime
import os
import re
import shutil

from six.moves.urllib.parse import urlsplit, urlunsplit

from vee.cli import style_note
from vee.pipeline.base import PipelineStep
from vee.utils import makedirs, http_request
from vee import log


class HttpTransport(PipelineStep):
    
    factory_priority = 1000

    @classmethod
    def factory(cls, step, pkg):
        if step == 'init' and re.match(r'^https?://', pkg.url):
            return cls(pkg)

    def get_next(self, step):
        if step in ('fetch', ):
            return self

    def init(self):

        pkg = self.package

        split = urlsplit(pkg.url)

        # Remove the fragment from the URL.
        pkg.url = urlunsplit((split.scheme, split.netloc, split.path, split.query, ''))

        pkg.package_name = os.path.join(split.netloc, split.path.strip('/'))

        # Retain the checksum if in the fragment.
        m = re.match(r'^(md5|sha1)[:=]([0-9a-fA-F]+)', split.fragment or '')
        if m:
            pkg.checksum = '%s:%s' % m.groups()

    def fetch(self):
        pkg = self.package
        pkg._assert_paths(package=True)
        if os.path.exists(pkg.package_path):
            log.info(style_note('Already downloaded', pkg.url))
            return
        log.info(style_note('Downloading', pkg.url))
        download(pkg.url, pkg.package_path)



def download(url, dst):

    makedirs(os.path.dirname(dst))

    tmp = dst + '.downloading'

    src_fh = None
    dst_fh = None
    try:
        src_fh = http_request('GET', url, preload_content=False)
        dst_fh = open(tmp, 'wb')
        # TODO: Indicate progress.
        for chunk in iter(lambda: src_fh.read(16384), b''):
            dst_fh.write(chunk)
    finally:
        if src_fh:
            src_fh.close()
        if dst_fh:
            dst_fh.close()

    shutil.move(tmp, dst)
