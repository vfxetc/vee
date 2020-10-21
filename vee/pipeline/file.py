import datetime
import os
import re
import shutil

from vee.cli import style, style_note
from vee.pipeline.base import PipelineStep
from vee.utils import makedirs, linktree
from vee import log


class FileTransport(PipelineStep):
    
    factory_priority = 100

    @classmethod
    def factory(cls, step, pkg):
        if step == 'init':
            return cls(pkg)
        if step == 'extract' and pkg.package_path and os.path.isdir(pkg.package_path):
            return cls(pkg)

    def get_next(self, step):
        if step in ('fetch', ):
            return self

    def init(self):
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

        log.info(style_note('Copying', 'to ' + pkg.package_path))

        source = os.path.expanduser(self._path)
        if os.path.isdir(source):
            shutil.copytree(source, pkg.package_path, symlinks=True)
        else:
            shutil.copyfile(source, pkg.package_path)

    def extract(self):

        pkg = self.package
        pkg._assert_paths(package=True, build=True)
        pkg._clean_build_path(makedirs=False)

        # We make sure we're passing unicode paths, so that it handles everything internally
        # as unicode. In python2 we have issues with getting it to handle non-ASCII characters
        # even when we set $LANG or $LC_ALL.
        package_path = pkg.package_path.decode() if isinstance(pkg.package_path, bytes) else pkg.package_path
        build_path = pkg.build_path.decode() if isinstance(pkg.build_path, bytes) else pkg.build_path

        if pkg.hard_link:
            linktree(package_path, build_path, symlinks=True,
                ignore=shutil.ignore_patterns('.git'),
            )
        else:
            shutil.copytree(package_path, build_path, symlinks=True,
                ignore=shutil.ignore_patterns('.git'),
            )
