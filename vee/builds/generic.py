import pkg_resources
import shutil

from vee.utils import style_note, style

_build_types = []


def get_package_builder(pkg):

    if not _build_types:
        _build_types[:] = [ep.load() for ep in pkg_resources.iter_entry_points('vee_build_types')]
        _build_types.sort(key=lambda cls: cls.factory_priority, reverse=True)

    for cls in _build_types:
        builder = cls.factory(pkg)
        if builder:
            return builder

    raise ValueError('no builder for %s' % pkg)


class GenericBuild(object):

    factory_priority = 0

    @classmethod
    def factory(cls, pkg):
        return cls(pkg)

    def __init__(self, pkg):
        self.package = pkg

    def build(self):
        print style_note('Generic package; nothing to build.')

    def install(self):
        pkg = self.package

        if pkg.make_install:
            print style('Warning:', 'yellow', bold=True), style('--make-install specified, but no Makefile found.', bold=True)

        print style('Installing via copy', 'blue', bold=True), style('to ' + pkg.install_path, bold=True)
        shutil.copytree(pkg.build_path_to_install, pkg.install_path_from_build, symlinks=True)
