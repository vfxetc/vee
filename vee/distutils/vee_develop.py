from __future__ import print_function

from distutils.cmd import Command
import os


class vee_develop(Command):

    description = "Handle VEE's Python development build."

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):

        build = self.distribution.get_command_obj('build_scripts')

        dev_path = os.path.abspath(os.path.join(__file__, '..', '..', '..', 'bin', 'dev'))
        build.executable = '%s --shebang python' % (
            dev_path,
            # TODO: Restore this functionality.
            #os.environ.get('VEE', ''),
            #os.environ.get('VEE_PYTHON', ''),
        )

        self.run_command('build_scripts')

        install = self.distribution.get_command_obj('install_scripts')
        install.install_dir = 'build/scripts'
        self.run_command('install_scripts')

        # Lets also call on the non-standard metatools.
        try:
            mt_scripts = self.distribution.get_command_obj('build_metatools_scripts')
        except Exception:
            print('missing build_metatools_scripts')
        else:
            mt_scripts.build_dir = 'build/scripts'
            self.run_command('build_metatools_scripts')
