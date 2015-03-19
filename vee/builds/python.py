import os
import sys

from vee.builds.generic import GenericBuild
from vee.cli import style, style_note, style_warning
from vee import log
from vee.envvars import join_env_path
from vee.subproc import call
from vee.utils import find_in_tree

python_version = '%d.%d' % (sys.version_info[:2])
site_packages = os.path.join('lib', 'python' + python_version, 'site-packages')


class PythonBuild(GenericBuild):

    type = 'python'

    factory_priority = 5000

    @classmethod
    def factory(cls, pkg):
        

        setup_path = find_in_tree(pkg.build_path, 'setup.py')
        egg_path = find_in_tree(pkg.build_path, 'EGG-INFO', 'dir')
        dist_path = find_in_tree(pkg.build_path, '*.dist-info', 'dir')

        if setup_path or egg_path or dist_path:
            return cls(pkg, (setup_path, egg_path, dist_path))

    def __init__(self, pkg, paths):
        super(PythonBuild, self).__init__(pkg)
        self.setup_path, self.egg_path, self.dist_path = paths

    def build(self):

        pkg = self.package

        if self.setup_path:

            log.info(style('Building Python package...', 'blue', bold=True))

            # Need to inject setuptools for this.
            cmd = ['python', '-c', 'import sys, setuptools; sys.argv[0]=__file__=\'setup.py\'; execfile(__file__)']
            cmd.extend(['build',
                '--executable', '/usr/bin/env python',
            ])
            cmd.extend(pkg.config)

            res = call(cmd, cwd=os.path.dirname(self.setup_path), env=pkg.fresh_environ(), indent=True, verbosity=1)
            if res:
                raise RuntimeError('Could not build Python package')

            return

        # python setup.py bdist_egg
        if self.egg_path:

            log.info(style('Found Python Egg:', 'blue', bold=True), style(os.path.basename(self.egg_path), bold=True))
            log.warning('Scripts and other data will not be installed.')

            if not pkg.package_path.endswith('.egg'):
                log.warning('package does not appear to be an Egg')

            # We must rename the egg!
            pkg_info_path = os.path.join(self.egg_path, 'PKG-INFO')
            if not os.path.exists(pkg_info_path):
                log.warning('EGG-INFO/PKG-INFO does not exist')
            else:
                pkg_info = {}
                for line in open(pkg_info_path, 'rU'):
                    line = line.strip()
                    if not line:
                        continue
                    name, value = line.split(':')
                    pkg_info[name.strip().lower()] = value.strip()
                try:
                    pkg_name = pkg_info['name']
                    pkg_version = pkg_info['version']
                except KeyError:
                    log.warning('EGG-INFO/PKG-INFO is malformed')
                else:
                    new_egg_path = os.path.join(os.path.dirname(self.egg_path), '%s-%s.egg-info' % (pkg_name, pkg_version))
                    shutil.move(self.egg_path, new_egg_path)
                    self.egg_path = new_egg_path

            pkg.build_subdir = os.path.dirname(self.egg_path)
            pkg.install_prefix = site_packages

            return

        # python setup.py bdist_wheel
        if self.dist_path:

            log.info(style('Found Python Wheel: ', 'blue', bold=True) + style(os.path.basename(self.dist_path), bold=True))
            log.warning('Scripts and other data will not be installed.')

            if not pkg.package_path.endswith('.whl'):
                log.warning('package does not appear to be a Wheel')

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

        log.info(style('Installing Python package...', 'blue', bold=True))

        # Need to inject setuptools for this.
        cmd = ['python', '-c', 'import sys, setuptools; sys.argv[0]=__file__=\'setup.py\'; execfile(__file__)']
        cmd.extend(['install',
            '--skip-build',
            '--root', pkg.install_path, # Better than prefix
            '--prefix', '.',
            '--install-lib', site_packages, # So that we don't get lib64; virtualenv symlinks them together anyways.
            # '--no-compile',
            '--single-version-externally-managed',
        ])

        
        res = call(cmd, cwd=os.path.dirname(self.setup_path), env=env,
                   indent=True, verbosity=1)
        if res:
            raise RuntimeError('Could not install Python package')

    def develop(self):
        pkg = self.package

        super(PythonBuild, self).develop()

        if self.setup_path:

            log.info(style_note('Building egg-info and scripts'))
            cmd = ['python', '-c', 'import sys,setuptools; __file__=sys.argv[0]=\'setup.py\'; execfile(__file__)']
            cmd.extend([
                'egg_info',
                'build_scripts', '-e', '/usr/bin/env VEE=%s VEE_PYTHON=%s dev python' % (os.environ.get("VEE", ''), os.environ.get('VEE_PYTHON', )),
                'install_scripts', '-d', 'build/scripts',
            ])
            if call(cmd, cwd=os.path.dirname(self.setup_path)):
                raise RuntimeError('Could not build egg-info')

            egg_info = find_in_tree(os.path.dirname(self.setup_path), '*.egg-info', 'dir')
            if not egg_info:
                raise RuntimeError('Could not find built egg-info')

            dirs_to_link = set()
            for line in open(os.path.join(egg_info, 'top_level.txt')):
                dirs_to_link.add(os.path.dirname(line.strip()))
            for name in sorted(dirs_to_link):
                log.info(style_note("Adding ./%s to $PYTHONPATH" % name))
                pkg.environ['PYTHONPATH'] = join_env_path('./' + name, pkg.environ.get('PYTHONPATH', '@'))

            scripts = os.path.join(os.path.dirname(self.setup_path), 'build', 'scripts')
            if os.path.exists(scripts):
                log.info(style_note("Adding ./build/scripts to $PATH"))
                pkg.environ['PATH'] = join_env_path('./build/scripts', pkg.environ.get('PATH', '@'))



