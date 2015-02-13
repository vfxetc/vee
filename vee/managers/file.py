import datetime
import os
import urllib2
import urlparse
import shutil

from vee.managers.base import BaseManager
from vee.utils import makedirs, colour


class FileManager(BaseManager):

    name = 'file'

    def fetch(self):

        if os.path.exists(self.package_path):
            print colour('Already copied.', 'blue', bright=True, reset=True)
            return

        makedirs(os.path.dirname(self.package_path))

        print colour('Downloading', 'blue', bright=True), colour(self.requirement.package, 'black', reset=True)
        print        '         to', colour(self.package_path, bright=True, reset=True)

        shutil.copyfile(os.path.expanduser(self.requirement.package), self.package_path)

