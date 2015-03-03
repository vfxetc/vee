import os
import sys

from vee.builds.generic import GenericBuild
from vee.utils import find_in_tree, style, call


python_version = '%d.%d' % (sys.version_info[:2])
site_packages = os.path.join('lib', 'python' + python_version, 'site-packages')



class PythonBuild(GenericBuild):

    factory_priority = 5000

    @classmethod
    def factory(cls, pkg):
        

        setup_path = find_in_tree(pkg.build_path, 'setup.py')
        egg_path = find_in_tree(pkg.build_path, '*.egg-info', 'dir')
        dist_path = find_in_tree(pkg.build_path, '*.dist-info', 'dir')

        if setup_path or egg_path or dist_path:
            return cls(pkg, (setup_path, egg_path, dist_path))

    def __init__(self, pkg, paths):
        super(PythonBuild, self).__init__(pkg)
        self.setup_path, self.egg_path, self.dist_path = paths

    def build(self):

        pkg = self.package

        if self.setup_path:

            print style('Building Python package...', 'blue', bold=True)

            # Need to inject setuptools for this.
            cmd = ['python', '-c', 'import setuptools; __file__=\'setup.py\'; execfile(__file__)']
            cmd.extend(['build',
                '--executable', '/usr/bin/env python',
            ])
            cmd.extend(pkg.config)

            if call(cmd, cwd=os.path.dirname(self.setup_path), env=pkg.fresh_environ()):
                raise RuntimeError('Could not build Python package')

            return

        if self.egg_path:

            print style('Found Python Egg:', 'blue', bold=True), style(os.path.basename(self.egg_path), bold=True)

            pkg.build_subdir = os.path.dirname(self.egg_path)
            pkg.install_prefix = site_packages

            return

        # This is very similar to the above...
        if self.dist_path:

            print style('Found Python Wheel:', 'blue', bold=True), style(os.path.basename(self.dist_path), bold=True)
            if not pkg.package_path.endswith('.whl'):
                print style('Warning:', 'yellow', bold=True), style('package does not appear to be a Wheel', bold=True)

            pkg.build_subdir = os.path.dirname(self.dist_path)
            pkg.install_prefix = site_packages

            return

    def install(self):

        if not self.setup_path:
            return super(PythonBuild, self).install()

        
        pkg = self.package

        install_site_packages = os.path.join(pkg.install_path, site_packages)

        # Setup the PYTHONPATH to point to the "install" directory.
        env = pkg.fresh_environ()
        env['PYTHONPATH'] = '%s:%s' % (install_site_packages, env.get('PYTHONPATH', ''))
        os.makedirs(install_site_packages)

        print style('Installing Python package...', 'blue', bold=True)

        # Need to inject setuptools for this.
        cmd = ['python', '-c', 'import setuptools; __file__=\'setup.py\'; execfile(__file__)']
        cmd.extend(['install',
            '--skip-build',
            '--root', pkg.install_path, # Better than prefix
            '--prefix', '.',
            '--install-lib', site_packages, # So that we don't get lib64.
            '--no-compile',
            '--single-version-externally-managed',
        ])

        if call(cmd, cwd=os.path.dirname(self.setup_path), env=env):
            raise RuntimeError('Could not install Python package')


