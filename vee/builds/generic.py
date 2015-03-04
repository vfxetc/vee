import os
import shutil

from vee.utils import style_note, style, envjoin


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
        pkg = self.package

        for name in ('bin', 'scripts'):
            path = os.path.join(pkg.build_path, name)
            if os.path.exists(path):
                print style_note("Adding ./%s to $PATH" % name)
                pkg.environ['PATH'] = envjoin('./' + name, pkg.environ.get('PATH', '@'))

