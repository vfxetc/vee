import os

from vee.pipeline.generic import GenericBuilder
from vee.cli import style_note
from vee.subproc import call
from vee.utils import find_in_tree
from vee import log


class MakeBuilder(GenericBuilder):

    factory_priority = 1000

    @classmethod
    def factory(cls, step, pkg):
        
        # We provide 'install' via get_next.
        if step != 'build':
            return

        configure_ac = find_in_tree(pkg.build_path, 'configure.ac')
        configure = find_in_tree(pkg.build_path, 'configure')
        makefile = find_in_tree(pkg.build_path, 'Makefile')

        if configure_ac and not configure and not pkg.autoconf:
            log.warning('autoconf detected, but --autoconf flag is not set on package')

        if (configure_ac and pkg.autoconf) or configure or makefile:
            return cls(pkg, (configure_ac, configure, makefile))

    def __init__(self, pkg, paths):
        super(MakeBuilder, self).__init__(pkg)
        self.configure_ac_path, self.configure_path, self.makefile_path = paths

    def build(self):

        pkg = self.package
        env = None

        if self.configure_ac_path and not self.configure_path:

            bootstrap = os.path.join(os.path.dirname(self.configure_ac_path), 'bootstrap')
            if os.path.exists(bootstrap):
                log.info(style_note('./bootstrap', '(autoreconf)'))
                cmd = ['./bootstrap']
            else:
                log.info(style_note('autoreconf'))
                cmd = ['autoreconf', '--install', '--force']

            env = env or pkg.fresh_environ()
            call(cmd, cwd=os.path.dirname(self.configure_ac_path), env=env)
            pkg.build_subdir = os.path.dirname(self.configure_ac_path)

            # Need to look for it again.
            self.configure_path = self.configure_path or find_in_tree(pkg.build_path, 'configure')

        if self.configure_path:

            log.info(style_note('./configure'))
            pkg._assert_paths(install=True)

            cmd = ['./configure', '--prefix', pkg.install_path]
            cmd.extend(pkg.config)
            env = env or pkg.fresh_environ()
            call(cmd, cwd=os.path.dirname(self.configure_path), env=env)

            pkg.build_subdir = os.path.dirname(self.configure_path)

        # Need to look for it again.
        self.makefile_path = self.makefile_path or find_in_tree(pkg.build_path, 'Makefile')

        if self.makefile_path:

            log.info(style_note('make'))

            env = env or pkg.fresh_environ()
            call(['make', '-j4'], cwd=os.path.dirname(self.makefile_path), env=env)

            pkg.build_subdir = os.path.dirname(self.makefile_path)

    def get_next(self, step):
        if step != 'install':
            return
        if self.makefile_path:
            if self.package.make_install:
                return self
            else:
                log.warning('Skipping `make install` and installing full package.\n'
                    'Usually you will want to specify one of:\n'
                    '    --make-install\n'
                    '    --build-subdir PATH\n'
                    '    --install-subdir PATH'
                )
    
    def install(self):
        pkg = self.package
        pkg._assert_paths(install=True)
        log.info(style_note('make install'))
        if call(
            ['make', 'install', '-j4'],
            cwd=os.path.dirname(self.makefile_path),
            env=pkg.fresh_environ(),
        ):
            raise RuntimeError('Could not `make install` package')

