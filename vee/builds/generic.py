import os
import shutil

from vee.cli import style_note, style
from vee.envvars import join_env_path
from vee import log


class GenericBuild(object):

    type = 'generic'
    
    factory_priority = 0

    @classmethod
    def factory(cls, pkg):
        return cls(pkg)

    def __init__(self, pkg):
        self.package = pkg

    def build(self):
        log.info(style_note('Generic package; nothing to build.'))

    def install(self):
        pkg = self.package

        if pkg.make_install:
            log.warning('--make-install specified, but no Makefile found.')

        log.info(style('Installing via copy ', 'blue', bold=True) + style('to ' + pkg.install_path, bold=True))
        shutil.copytree(pkg.build_path_to_install, pkg.install_path_from_build, symlinks=True)

    def develop(self):
        pkg = self.package

        for name in ('bin', 'scripts'):
            path = os.path.join(pkg.build_path, name)
            if os.path.exists(path):
                log.info(style_note("Adding ./%s to $PATH" % name))
                pkg.environ['PATH'] = join_env_path('./' + name, pkg.environ.get('PATH', '@'))

