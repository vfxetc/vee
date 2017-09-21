import os
import subprocess

__version__ = '0.2.0'

try:
    __revision__ = subprocess.check_output(['git', 'describe', '--tags', '--always', '--dirty'], cwd=os.path.dirname(__file__)).strip()
except subprocess.CalledProcessError:
    __revision__ = 'unknown'

