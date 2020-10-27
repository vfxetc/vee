import os
import re
import subprocess
import sys


class Python(object):

    def __init__(self, executable, version):
        self.executable = executable
        self.version = version

    def __repr__(self):
        return 'Python({!r}, {!r})'.format(self.executable, self.version)

    @property
    def major(self):
        return self.version[0]

    @property
    def minor(self):
        return self.version[1]


def get_python(selector=None):

    selector = selector or os.environ.get('VEE_PYTHON')
    if not selector:
        return Python(sys.executable, sys.version_info)

    version = executable = None

    if isinstance(selector, str):

        m = re.match(r'(?:python)?(\d)(?:\.(\d+)(?:\.(\d+))?)?', selector)
        if m:
            major, minor, patch = m.groups()
            if minor:
                version = (int(major), int(minor))
                executable = 'python{}.{}'.format(*version)
            else:
                executable = 'python{}'.format(major)

    elif isinstance(selector, int):
        executable = 'python{}'.format(selector)

    elif isinstance(selector, (list, tuple)):
        version = tuple(selector)
        if len(version) < 2:
            raise ValueError("version sequence must have 2 elements")
        if not (isinstance(version[0], int) and isinstance(version[1], int)):
            raise ValueError("version sequence must contain ints")

    if not version:
        
        if not executable:
            executable = selector
        
        proc = subprocess.Popen([executable, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        out = (out + err).decode().strip()

        m = re.match(r'Python (\d)\.(\d+)\.(\d+)', out)
        if not m:
            raise ValueError("could not parse output of `{} --version`".format(executable))
        version = tuple(map(int, m.groups()))

    if version and not executable:
        executable = 'python{}.{}'.format(*version)

    return Python(executable, version)


_default_python = None

def get_default_python():
    global _default_python
    if _default_python is None:
        _default_python = get_python()
    return _default_python


if __name__ == '__main__':
    print(get_default_python())

