import os
import subprocess

__version__ = '0.1-dev'
__revision__ = subprocess.check_output(['git', 'describe', '--tags', '--always', '--dirty'], cwd=os.path.dirname(__file__)).strip()
