import datetime
import os
import urllib2
import urlparse
import shutil

from vee.packages.base import BasePackage
from vee.utils import makedirs, style


class FilePackage(BasePackage):

    type = 'file'

    def __init__(self, *args, **kwargs):
        super(FilePackage, self).__init__(*args, **kwargs)
        self.url = os.path.abspath(os.path.expanduser(self.url))
    
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

        print style('Copying', 'blue', bold=True), style(self.url, bold=True)
        print        '         to', style(self.package_path, bold=True)

        source = os.path.expanduser(self.url)
        if os.path.isdir(source):
            shutil.copytree(source, self.package_path, symlinks=True)
        else:
            shutil.copyfile(source, self.package_path)

