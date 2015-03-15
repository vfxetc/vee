import os

from vee.builds.generic import GenericBuild
from vee.cli import style
from vee.subproc import call
from vee.utils import find_in_tree
from vee import log


class MakeBuild(GenericBuild):

    type = 'make'

    factory_priority = 1000

    @classmethod
    def factory(cls, pkg):
        
        configure = find_in_tree(pkg.build_path, 'configure')
        makefile = find_in_tree(pkg.build_path, 'Makefile')

        if configure or makefile:
            return cls(pkg, (configure, makefile))

    def __init__(self, pkg, paths):
        super(MakeBuild, self).__init__(pkg)
        self.configure_path, self.makefile_path = paths

    def build(self):

        pkg = self.package
        env = None

        if self.configure_path:

            log.info(style('Configuring...', 'blue', bold=True))

            cmd = ['./configure', '--prefix', pkg.install_path]
            cmd.extend(pkg.config)
            env = env or pkg.fresh_environ()
            call(cmd, cwd=os.path.dirname(self.configure_path), env=env)

            pkg.build_subdir = os.path.dirname(self.configure_path)

        # Need to look for it again.
        self.makefile_path = self.makefile_path or find_in_tree(pkg.build_path, 'Makefile')

        if self.makefile_path:

            log.info(style('Making...', 'blue', bold=True))

            env = env or pkg.fresh_environ()
            call(['make', '-j4'], cwd=os.path.dirname(self.makefile_path), env=env)

            pkg.build_subdir = os.path.dirname(self.makefile_path)

    def install(self):

        if not self.makefile_path:
            return super(MakeBuild, self).install()

        pkg = self.package

        if not pkg.make_install:
            log.warning('Skipping `make install` and installing full package.\n'
                'Usually you will want to specify one of:\n'
                '    --make-install\n'
                '    --build-subdir PATH\n'
                '    --install-subdir PATH'
            )
            return super(MakeBuild, self).install()

        log.info(style('Installing via `make install`', 'blue', bold=True))
        if call(
            ['make', 'install', '-j4'],
            cwd=os.path.dirname(self.makefile_path),
            env=pkg.fresh_environ(),
        ):
            raise RuntimeError('Could not `make install` package')

