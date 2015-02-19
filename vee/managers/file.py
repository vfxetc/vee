import datetime
import os
import urllib2
import urlparse
import shutil

from vee.managers.base import BaseManager
from vee.utils import makedirs, style


class FileManager(BaseManager):

    name = 'file'

    def fetch(self):

        self._assert_paths(package=True)

        # Don't shortcut on files.
        if False and os.path.exists(self.package_path):
            print style('Already copied.', 'blue', bold=True)
            return

        if os.path.exists(self.package_path):
            if os.path.isdir(self.package_path):
                shutil.rmtree(self.package_path)
            else:
                os.unlink(self.package_path)
        
        makedirs(os.path.dirname(self.package_path))

        print style('Copying', 'blue', bold=True), style(self.requirement.package, bold=True)
        print        '         to', style(self.package_path, bold=True)

        source = os.path.expanduser(self.requirement.package)
        if os.path.isdir(source):
            shutil.copytree(source, self.package_path)
        else:
            shutil.copyfile(source, self.package_path)

