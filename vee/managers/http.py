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
    def _local_path(self):
        split = urlparse.urlsplit(self.requirement.package)
        return self.home.abspath(
            'packages',
            self.name,
            split.netloc,
            split.path.strip('/'),
        )

    def fetch(self):

        if os.path.exists(self._local_path):
            self._local_path

        makedirs(os.path.dirname(self._local_path))

        temp = self._local_path + '.downloading'

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

        shutil.move(temp, self._local_path)

        return self._local_path

