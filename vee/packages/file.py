import datetime
import os
import re
import shutil
import urllib2
import urlparse

from vee.cli import style
from vee.packages.base import BasePackage
from vee.utils import makedirs
from vee import log


class FilePackage(BasePackage):

    type = 'file'
    
    factory_priority = 0

    @classmethod
    def factory(cls, req, home):
        return cls(req, home)

    def __init__(self, *args, **kwargs):
        super(FilePackage, self).__init__(*args, **kwargs)
        self._url_path = re.sub(r'^file:|#.*$', '', self.url)
        self.url = 'file:' + self._url_path
        self.package_name = os.path.expanduser(self._url_path).strip('/')
    
    def fetch(self):

        self._assert_paths(package=True)

        if os.path.exists(self.package_path):
            if os.path.isdir(self.package_path):
                shutil.rmtree(self.package_path)
            else:
                os.unlink(self.package_path)
        
        makedirs(os.path.dirname(self.package_path))

        log.info(style('Copying', 'blue', bold=True), style(self._url_path, bold=True))

        source = os.path.expanduser(self._url_path)
        if os.path.isdir(source):
            shutil.copytree(source, self.package_path, symlinks=True)
        else:
            shutil.copyfile(source, self.package_path)

