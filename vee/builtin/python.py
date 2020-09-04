import copy
import os
import re
import subprocess
import sys
import venv

import virtualenv

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

            config = which('python{}-config'.format(version))
            if not config:
                continue

            prefix = subprocess.check_output([config, '--prefix']).decode().strip()
            bin_dir = os.path.join(prefix, 'bin')
            base_exec_path = os.path.join(bin_dir, 'python')

            for postfix in (version, ''):
                exec_path = base_exec_path + postfix
                if not os.path.exists(exec_path):
                    continue
                proc = subprocess.Popen([exec_path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = proc.communicate()
                raw_version = (out.strip() + err.strip()).decode().strip()
                break
            else:
                raise ValueError("could not find python binary in {}".format(bin_dir))

            m = re.match(r'^Python ([\d\.]+)$', raw_version)
            if not m:
                raise ValueError("could not parse python version {!r} from {}".format(raw_version, path))

            version = m.group(1)

            self.variants.append({
                'provides': {'version': version},
                # 'environ': {
                #     "PATH": "{}:@".format(bin_dir)
                # }
            })

            self._exec_paths[version] = exec_path

            return True

    def init(self, pkg):
        pkg.variants = copy.deepcopy(self.variants)

    def fetch(self, pkg):
        pass

    def extract(self, pkg):
        pass

    def inspect(self, pkg):
        pkg._assert_paths(install=True)

    def build(self, pkg):
        pass

    def install(self, pkg):

        version = str(pkg.provides['version'])
        exec_path = self._exec_paths[version]

        # print("creating virtualenv {}".format(pkg.install_path))
        virtualenv.cli_run(['--python', exec_path, '--no-pip', '--no-wheel', '--no-setuptools', pkg.install_path])
