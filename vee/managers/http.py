import datetime
import os
import urllib2
import urlparse
import shutil

from vee.managers.base import BaseManager
from vee.utils import makedirs, colour


class HttpManager(BaseManager):

    name = 'http'

    @property
    def _derived_package_name(self):
        split = urlparse.urlsplit(self.requirement.package)
        return os.path.join(
            split.netloc,
            split.path.strip('/'),
        )

    def fetch(self):

        self._assert_paths(package=True)

        if os.path.exists(self.package_path):
            print colour('Already downloaded.', 'blue', bold=True, reset=True)
            return

        makedirs(os.path.dirname(self.package_path))

        temp = self.package_path + '.downloading'

        print colour('Downloading', 'blue', bold=True), colour(self.requirement.package, 'black', reset=True)
        print        '         to', colour(self.package_path, bold=True, reset=True)

        src_fh = None
        dst_fh = None
        try:
            src_fh = urllib2.urlopen(self.requirement.package)
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

