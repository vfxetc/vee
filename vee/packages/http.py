import datetime
import os
import urllib2
import urlparse
import shutil

from vee.packages.base import BasePackage
from vee.utils import makedirs, style


class HttpPackage(BasePackage):

    name = 'http'

    @property
    def _derived_package_name(self):
        split = urlparse.urlsplit(self.requirement.url)
        return os.path.join(
            split.netloc,
            split.path.strip('/'),
        )

    def fetch(self):

        self._assert_paths(package=True)

        if os.path.exists(self.package_path):
            print style('Already downloaded.', 'blue', bold=True)
            return

        makedirs(os.path.dirname(self.package_path))

        temp = self.package_path + '.downloading'

        print style('Downloading', 'blue', bold=True), style(self.requirement.url, bold=True)
        print        '         to', style(self.package_path, bold=True)

        src_fh = None
        dst_fh = None
        try:
            src_fh = urllib2.urlopen(self.requirement.url)
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

