import datetime
import os
import urllib2
import urlparse
import re
import shutil

from vee.cli import style_note
from vee.pipeline.base import PipelineStep
from vee.utils import makedirs
from vee import log


class HttpTransport(PipelineStep):
    
    factory_priority = 1000

    @classmethod
    def factory(cls, step, pkg, *args):
        if step != 'fetch':
            return
        if re.match(r'^https?://', pkg.url):
            return cls(pkg, *args)

    def fetch(self):
        pkg = self.package

        split = urlparse.urlsplit(pkg.url)
        pkg.package_name = os.path.join(split.netloc, split.path.strip('/'))
        pkg._assert_paths(package=True)

        if os.path.exists(pkg.package_path):
            log.info(style_note('Already downloaded', pkg.url))
            return
        log.info(style_note('Downloading', pkg.url))
        download(pkg.url, pkg.package_path)



def download(url, dst):

    makedirs(os.path.dirname(dst))

    temp = dst + '.downloading'

    src_fh = None
    dst_fh = None
    try:
        src_fh = urllib2.urlopen(url)
        dst_fh = open(temp, 'wb')
        # TODO: Indicate progress.
        for chunk in iter(lambda: src_fh.read(16384), ''):
            dst_fh.write(chunk)
    finally:
        if src_fh:
            src_fh.close()
        if dst_fh:
            dst_fh.close()

    shutil.move(temp, dst)
