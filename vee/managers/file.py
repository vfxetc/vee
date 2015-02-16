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

        # Don't shortcut on files.
        if False and os.path.exists(self.package_path):
            print colour('Already copied.', 'blue', bright=True, reset=True)
            return

        if os.path.exists(self.package_path):
            if os.path.isdir(self.package_path):
                shutil.rmtree(self.package_path)
            else:
                os.unlink(self.package_path)
        
        makedirs(os.path.dirname(self.package_path))

        print colour('Copying', 'blue', bright=True), colour(self.requirement.package, 'black', reset=True)
        print        '         to', colour(self.package_path, bright=True, reset=True)

        source = os.path.expanduser(self.requirement.package)
        if os.path.isdir(source):
            shutil.copytree(source, self.package_path)
        else:
            shutil.copyfile(source, self.package_path)

