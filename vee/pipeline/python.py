import os
import re
import shutil
import sys

from vee import log
from vee.cli import style, style_note, style_warning
from vee.envvars import join_env_path
from vee.package import Package
from vee.pipeline.generic import GenericBuilder
from vee.subproc import call
from vee.utils import find_in_tree


# TODO: This should be the requested version.
python_version = '2.7' # '%d.%d' % (sys.version_info[:2])
site_packages = os.path.join('lib', 'python' + python_version, 'site-packages')


def call_setup_py(setup_py, args, **kwargs):
    kwargs['cwd'] = os.path.dirname(setup_py)
    kwargs.setdefault('vee_in_env', True)
    # TODO: This should be the requested version.
    cmd = ['python2.7', '-c', 'import sys, setuptools; sys.argv[0]=__file__=%r; execfile(__file__)' % os.path.basename(setup_py)]
    cmd.extend(('--command-packages', 'vee.distutils'))
    cmd.extend(args)
    return call(cmd, **kwargs)


class DummyPipRequirement(object):
    pass

class PythonBuilder(GenericBuilder):

    factory_priority = 5000

    @classmethod
    def factory(cls, step, pkg):

        if step != 'inspect':
            return

        setup_path = find_in_tree(pkg.build_path, 'setup.py')
        dist_path  = find_in_tree(pkg.build_path, '*.dist-info', 'dir')

        if setup_path or dist_path:
            return cls(pkg, (setup_path, dist_path))

    def get_next(self, name):
        if name in ('build', 'install', 'develop'):
            return self
    
    def __init__(self, pkg, paths):
        super(PythonBuilder, self).__init__(pkg)
        self.setup_path, self.dist_info_dir = paths

    
    def inspect(self):

        pkg = self.package

        if self.setup_path:

            self.egg_path = find_in_tree(pkg.build_path, '*.egg-info', 'dir')
            if not self.egg_path:

                log.info(style_note('Building Python egg-info'))
                res = call_setup_py(self.setup_path, ['egg_info'], env=pkg.fresh_environ(), indent=True, verbosity=1)
                if res:
                    raise RuntimeError('Could not build Python package')

                self.egg_path = find_in_tree(pkg.build_path, '*.egg-info', 'dir')
                if not self.egg_path:
                    log.warning('Could not find newly created *.egg-info')
                    return

            requires_path = os.path.join(self.egg_path, 'requires.txt')
            if os.path.exists(requires_path):
                for line in open(requires_path, 'r'):
                    
                    # Stop once we get to the "extras".
                    if line.startswith('['):
                        break

                    m = re.match(r'^([\w\.-]+)', line)
                    if m:
                        name = m.group(1).lower()
                        log.debug('%s depends on %s' % (pkg.name, name))
                        pkg.add_dependency(name=name, url='pypi:%s' % name)

        if self.dist_info_dir:

            for line in open(os.path.join(self.dist_info_dir, 'METADATA')):

                line = line.strip()
                if not line:
                    break # We're at the end of the headers.

                key, value = line.split(': ', 1)
                key = key.lower()

                if key == 'requires-dist':

                    # Environmental markers look like `FOO; extra == 'BAR'`.
                    if ';' in value:

                        value, raw_marker = value.split(';')
                        value = value.strip()

                        # We delay the import just in case the bootstrap is borked.
                        from packaging.markers import Marker

                        marker = Marker(raw_marker)
                        if not marker.evaluate({'extra': None}):
                            continue

                    m = re.match(r'([\w-]+)(?:\s+\(([^)]+)\))?', value)
                    if not m:
                        log.warning('Could not parse requires-dist {!r}'.format(value))
                        continue

                    dep_name, version_expr = m.groups()
                    pkg.add_dependency(
                        name=dep_name,
                        url='pypi:{}'.format(dep_name),
                        revision=version_expr,
                    )

    def build(self):

        pkg = self.package

        if self.setup_path:

            # Some packages need to be built at the same time as installing.
            # Anything which uses the distutils install_clib command, for instance...
            if pkg.defer_setup_build:
                log.info(style_note('Deferring build to install stage'))
                return

            log.info(style_note('Building Python package'))

            cmd = ['build']
            cmd.extend(pkg.config)

            res = call_setup_py(self.setup_path, cmd, env=pkg.fresh_environ(), indent=True, verbosity=1)
            if res:
                raise RuntimeError('Could not build Python package')

    def install(self):
        if self.setup_path:
            self._install_setup()
        elif self.dist_info_dir:
            self._install_wheel()
        else:
            return super(PythonBuilder, self).install()

    def _install_setup(self):

        pkg = self.package
        pkg._assert_paths(install=True)

        install_site_packages = os.path.join(pkg.install_path, site_packages)

        # Setup the PYTHONPATH to point to the "install" directory.
        env = pkg.fresh_environ()
        env['PYTHONPATH'] = join_env_path(install_site_packages, env.get('PYTHONPATH'))
        
        if os.path.exists(pkg.install_path):
            log.warning('Removing existing install', pkg.install_path)
            shutil.rmtree(pkg.install_path)
        os.makedirs(install_site_packages)

        log.info(style_note('Installing Python package', 'to ' + install_site_packages))

        cmd = [
        
            'install',
            '--root', pkg.install_path, # Better than prefix
            '--prefix', '.',

            # At one point we forced everything into `lib`, so we don't get a
            # `lib64`. Virtualenv symlinked them together anyways. But then we
            # switched to using pip's internals to unpack wheels, and it would
            # place stuff into both `lib` and `lib64`. So we don't really
            # know where we stand on this anymore.
            '--install-lib', site_packages,

            '--single-version-externally-managed',
        ]
        if not pkg.defer_setup_build:
            cmd.append('--skip-build')
        
        res = call_setup_py(self.setup_path, cmd, env=env, indent=True, verbosity=1)
        if res:
            raise RuntimeError('Could not install Python package')

    def _install_wheel(self):

        pkg = self.package
        pkg._assert_paths(install=True)

        if pkg.package_path.endswith('.whl'):
            log.info(style_note("Found Python Wheel", os.path.basename(self.dist_info_dir)))
        else:
            log.info(style_note("Found dist-info", os.path.basename(self.dist_info_dir)))
            log.warning("Bare dist-info does not appear to be a wheel.")

        wheel_dir, dist_info_name = os.path.split(self.dist_info_dir)
        wheel_name = os.path.splitext(dist_info_name)[0]

        # Lets just take advantage of pip!
        # The only reason we're reading into pip like this is because we
        # would rather just do this part, rather than have it go through
        # the full process with the *.whl file. If this breaks, feel
        # free to do something like:
        #     pip install --force-reinstall --prefix {pkg.install_path} --no-deps {pkg.package_path}
        # along with:
        #     --no-warn-script-location
        #     --disable-pip-version-check

        # We delay the import just in case the bootstrap is borked.
        from pip._internal.operations.install.wheel import install_wheel
        from pip._internal.locations import get_scheme

        # HACK: We want to install this for Python2.7 for now. This should
        # be based on the version of Python that is a dependency.
        scheme = get_scheme(self.name, prefix=pkg.install_path)
        src_python = f'/python{sys.version_info[0]}.{sys.version_info[1]}/'
        dst_python = '/python2.7/'
        if src_python != dst_python:
            for k in 'platlib', 'purelib', 'headers', 'scripts', 'data':
                setattr(scheme, k, getattr(scheme, k).replace(src_python, dst_python))

        req = DummyPipRequirement()
        req.name = wheel_name
        install_wheel(pkg.name, pkg.package_path, scheme, '<VEE dummy request>')

    def develop(self):
        pkg = self.package

        log.info(style_note('Building scripts'))
        cmd = ['vee_develop']
        if call_setup_py(self.setup_path, cmd):
            raise RuntimeError('Could not build scripts')

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



