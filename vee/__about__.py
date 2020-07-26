import os
import subprocess

__version__ = '1.0.0.dev0'

try:
    __revision__ = subprocess.check_output([
    	'git', 'describe', '--tags', '--always', '--dirty'
    ], cwd=os.path.dirname(__file__)).strip().decode()
except subprocess.CalledProcessError:
    __revision__ = 'unknown'

