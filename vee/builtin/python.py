import subprocess
import sys
import venv

from vee.utils import which




class Package:

    variants = []

    _exec_paths = {}

    def __init__(self):

        if not self.variants:

            self._add_first_version(('2', '2.7'))

            # Add the first 3 we find, starting with the generic one.
            threes = ['3']
            assert sys.version_info[0] == 3
            for minor in range(max(sys.version_info[1], 7), 3, -1):
                threes.append('3.{}'.format(minor))
            self._add_first_version(threes)

    def _add_first_version(self, versions):

        for version in versions:

            config = which('python-config{}'.format(version))
            if not config:
                continue

            prefix = subprocess.check_output([config, '--prefix'])
            bin_dir = os.path.join(path, 'bin')
            exec_path = os.path.join(bin_dir, 'python')

            raw_version = subprocess.check_output([exec_path, '--version'])
            m = re.match(r'Python ([\d\.+])')
            if not m:
                raise ValueError("could not parse python version {!r} from {}".format(raw_version, exec_path))

            version = m.group(1)

            variants.append({
                'provides': {'version': version},
                'environ': {
                    "PATH": "{}:@".format(bin_dir)
                }
            })

            self._exec_paths[version] = exec_path

            return True

    def fetch(self, pkg):
        pass

    def extract(self, pkg):
        pass

    def inspect(self, pkg):
        pass

    def build(self, pkg):
        pass

    def install(self, pkg):

        version = pkg.provides['version']
        exec_path = self._exec_paths[version]

        venv.main(['--python', exec_path, pkg.install_path])
