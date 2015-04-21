import re

from vee.pipeline.base import PipelineStep
from vee.subproc import call
from vee.cli import style_note
from vee import log
from vee.utils import assert_file_checksum


class ArchiveExtractor(PipelineStep):

    factory_priority = 2000

    @classmethod
    def factory(cls, step, pkg):

        if step != 'extract':
            return

        pkg._assert_paths(package=True)

        if re.search(r'(\.tgz|\.tar\.gz)$', pkg.package_path):
            return cls(pkg, 'tar+gzip')

        if re.search(r'(\.tbz|\.tar\.bz2)$', pkg.package_path):
            return cls(pkg, 'tar+bzip')

        if re.search(r'(\.zip|\.egg|\.whl)$', pkg.package_path):
            return cls(pkg, 'zip')

    def __init__(self, pkg, archive_type):
        super(ArchiveExtractor, self).__init__(pkg)
        self.archive_type = archive_type
    
    def extract(self):
        """Extract the package into the (cleaned) build directory."""

        pkg = self.package
        pkg._assert_paths(build=True)

        if pkg.checksum:
            log.info(style_note('Verifying checksum', 'of ' + pkg.package_path), verbosity=1)
            assert_file_checksum(pkg.package_path, pkg.checksum)

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
