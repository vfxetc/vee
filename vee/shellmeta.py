import os

from vee.subproc import bash_source


class ShellMeta(object):

    def __init__(self, path):
        self._path = path
        self._functions = None

    def _has_function(self, name):
        if self._functions is None:
            output = bash_source(self._path, epilogue='echo ===; compgen -A function', stdout=True).decode()
            self._functions = set()
            for line in output.split('===')[-1].splitlines():
                self._functions.add(line.strip())
        return name in self._functions

    @property
    def build(self):
        if self._has_function('build'):
            return self._build

    @property
    def install(self):
        if self._has_function('install'):
            return self._install

    def _get_env(self, pkg):
        env = os.environ.copy()
        env['VEE_BUILD_PATH'] = pkg.build_path or ''
        env['VEE_INSTALL_PATH'] = pkg.install_path or ''
        return env

    def _call(self, pkg, name):
        bash_source(self._path, epilogue='''
            {} "$VEE_BUILD_PATH" "$VEE_INSTALL_PATH"
        '''.format(name), cwd=pkg.build_path, env=self._get_env(pkg))

    def _build(self, pkg):
        pkg._assert_paths(install=True)
        self._call(pkg, 'build')

    def _install(self, pkg):
        pkg._assert_paths(install=True)
        self._call(pkg, 'install')

