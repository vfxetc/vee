import datetime
import os
import re
import shutil
import urllib2
import urlparse

from vee.cli import style
from vee.pipeline.base import PipelineStep
from vee.utils import makedirs
from vee import log


class FileTransport(PipelineStep):
    
    factory_priority = 0

    @classmethod
    def factory(cls, step, pkg, *args):
        if step in ('fetch', 'extract'):
            return cls(pkg, *args)

    def __init__(self, *args, **kwargs):
        super(FileTransport, self).__init__(*args, **kwargs)
        pkg = self.package
        self._path = re.sub(r'^file:|#.*$', '', pkg.url)
        pkg.url = 'file:' + self._path
        pkg.package_name = os.path.expanduser(self._path).strip('/')
    
    def fetch(self):

        pkg = self.package
        pkg._assert_paths(package=True)

        if os.path.exists(pkg.package_path):
            if os.path.isdir(pkg.package_path):
                shutil.rmtree(pkg.package_path)
            else:
                os.unlink(pkg.package_path)
        
        makedirs(os.path.dirname(pkg.package_path))

        log.info(style('Copying', 'blue', bold=True), style(self._path, bold=True))

        source = os.path.expanduser(self._path)
        if os.path.isdir(source):
            shutil.copytree(source, pkg.package_path, symlinks=True)
        else:
            shutil.copyfile(source, pkg.package_path)

    def extract(self):

        pkg = self.package
        pkg._assert_paths(package=True, build=True)
        pkg._clean_build_path(makedirs=False)

        if pkg.hard_link:
            linktree(pkg.package_path, pkg.build_path, symlinks=True,
                ignore=shutil.ignore_patterns('.git'),
            )
        else:
            shutil.copytree(pkg.package_path, pkg.build_path, symlinks=True,
                ignore=shutil.ignore_patterns('.git'),
            )
