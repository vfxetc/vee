import os
import re

from vee.subproc import bash_source


class ShellMeta(object):

    def __init__(self, path):

        self._path = path
        self._functions = set()
        self._variables = {}

        output = bash_source(self._path, epilogue='''
            for _name in $(compgen -A function); do
                echo "#vee function $_name"
            done
            for _name in $(compgen -A variable); do
                _value="${!_name}"
                echo "#vee variable $_name ${#_value} $_value"
            done
        ''', stdout=True)

        for m in re.finditer(rb'^#vee function (\S+)$', output, flags=re.MULTILINE):
            self._functions.add(m.group(1).decode())

        for m in re.finditer(rb'^#vee variable (\S+) (\d+) ', output, flags=re.MULTILINE):
            name = m.group(1).decode()
            len_ = int(m.group(2))
            value = output[m.end():m.end() + len_].decode()
            self._variables[name] = value

    @property
    def url(self):
        return self._variables.get('url')
    
    @property
    def build(self):
        if 'build' in self._functions:
            return self._build

    @property
    def install(self):
        if 'install' in self._functions:
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

