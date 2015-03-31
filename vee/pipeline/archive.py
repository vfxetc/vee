import re

from vee.pipeline.base import PipelineStep
from vee.subproc import call
from vee.cli import style_note
from vee import log


class ArchiveExtractor(PipelineStep):

    type = 'archive'

    factory_priority = 2000

    @classmethod
    def factory(cls, step, pkg, *args):

        if step != 'extract':
            return

        pkg._assert_paths(package=True)

        if re.search(r'(\.tgz|\.tar\.gz)$', pkg.package_path):
            return cls(pkg, 'tar+gzip', *args)

        if re.search(r'(\.tbz|\.tar\.bz2)$', pkg.package_path):
            return cls(pkg, 'tar+bzip', *args)

        if re.search(r'(\.zip|\.egg|\.whl)$', pkg.package_path):
            return cls(pkg, 'zip', *args)

    def __init__(self, pkg, archive_type, *args):
        super(ArchiveExtractor, self).__init__(pkg, *args)
        self.archive_type = archive_type
    
    def extract(self):
        """Extract the package into the (cleaned) build directory."""

        pkg = self.package
        pkg._assert_paths(build=True)
        log.info(style_note('Expanding %s to' % self.archive_type, pkg.build_path))

        pkg._clean_build_path()

        # gzip-ed Tarballs.
        if self.archive_type == 'tar+gzip':
            call(['tar', 'xzf', pkg.package_path], cwd=pkg.build_path)
        
        # bzip-ed Tarballs.
        elif self.archive_type == 'tar+bzip':
            call(['tar', 'xjf', pkg.package_path], cwd=pkg.build_path)

        # Zip files (and Python wheels).
        elif self.archive_type == 'zip':
            call(['unzip', pkg.package_path], cwd=pkg.build_path)
