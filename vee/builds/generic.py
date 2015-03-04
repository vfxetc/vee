import shutil

from vee.utils import style_note, style


class GenericBuild(object):

    type = 'generic'
    
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

    def develop(self):
        print style_note('Generic package; nothing to setup for development.')
