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
    def package_name(self):
        split = urlparse.urlsplit(self.requirement.package)
        return os.path.join(
            split.netloc,
            split.path.strip('/'),
        )

    def fetch(self):

        if os.path.exists(self.package_path):
            self.package_path

        makedirs(os.path.dirname(self.package_path))

        temp = self.package_path + '.downloading'

        print colour('VEE Downloading', 'blue', bright=True), colour(self.requirement.package, 
            'black') + colour('', reset=True)

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

        return self.package_path

