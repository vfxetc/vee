import os
import shutil

from vee.cli import style_note
from vee.envvars import join_env_path
from vee import log
from vee.utils import find_in_tree, linktree
from vee.subproc import call, bash_source
from vee.pipeline.base import PipelineStep


class GenericBuilder(PipelineStep):
    
    factory_priority = 0

    @classmethod
    def factory(cls, step, pkg):
        if step in ('init', 'inspect', 'build', 'install', 'develop'):
            return cls(pkg)

    def init(self):
        pass
    
    def inspect(self):
        pass

    def build(self):
        log.info(style_note('Generic package; nothing to build.'), verbosity=1)

    def install(self):

        pkg = self.package
        pkg._assert_paths(install=True)

        if pkg.make_install:
            log.warning('--make-install specified, but no Makefile found.')

        if os.path.exists(pkg.install_path):
            log.warning('Removing existing install')
            shutil.rmtree(pkg.install_path)

        if pkg.hard_link:
            log.info(style_note('Installing via hard-link', 'to ' + pkg.install_path))
            linktree(pkg.build_path_to_install, pkg.install_path_from_build, symlinks=True)
        else:
            log.info(style_note('Installing via copy', 'to ' + pkg.install_path))
            shutil.copytree(pkg.build_path_to_install, pkg.install_path_from_build, symlinks=True)

    def develop(self):
        pkg = self.package
        for name in ('bin', 'scripts'):
            path = os.path.join(pkg.build_path, name)
            if os.path.exists(path):
                log.info(style_note("Adding ./%s to $PATH" % name))
                pkg.environ['PATH'] = join_env_path('./' + name, pkg.environ.get('PATH', '@'))

