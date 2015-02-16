import atexit
import os
import shutil
import subprocess

from unittest import TestCase


tests_dir = os.path.abspath(os.path.join(__file__, '..'))
root_dir = os.path.dirname(tests_dir)
assets_dir = os.path.join(tests_dir, 'assets') 
sandbox_dir = os.path.join(tests_dir, 'sandbox')



def vee(*args, **kwargs):

    stdout=kwargs.pop('stdout', False)
    cwd=kwargs.pop('cwd', None) or sandbox()
    home=kwargs.pop('home', None) or sandbox()

    env = os.environ.copy()
    env['VEE'] = home
    env['PYTHONPATH'] = root_dir
    cmd = ['python', '-m', 'vee']
    cmd.extend(args)
    print '$', ' '.join(cmd)
    if stdout:
        return subprocess.check_output(cmd, cwd=cwd, env=env, **kwargs)
    else:
        return subprocess.call(cmd, cwd=cwd, env=env, **kwargs)


def http(path=''):
    port = 9080
    if http.proc is None:
        http.proc = subprocess.Popen(['python', '-m', 'SimpleHTTPServer', str(port)], cwd=assets_dir)
        @atexit.register
        def shutdown():
            http.proc.terminate()
            http.proc.kill()
    return 'http://localhost:%d/%s' % (port, path.rstrip('/'))

http.proc = None



def sandbox(*args):
    if not sandbox.cleared:
        if os.path.exists(sandbox_dir):
            shutil.rmtree(sandbox_dir)
        sandbox.cleared = True
        os.makedirs(sandbox_dir)
    path = os.path.join(sandbox_dir, *args)
    return path

sandbox.cleared = False

