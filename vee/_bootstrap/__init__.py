import os
import sys
import urllib
import subprocess

from vee.utils import makedirs


vendored_packages = ['setuptools', 'wheel', 'packaging', 'virtualenv']
vendor_prefix = os.path.abspath(os.path.join(__file__, '..', '..', '..', 'build', 'vendor'))
vendor_path = os.path.join(vendor_prefix, 'lib', 'python{0.major}.{0.minor}'.format(sys.version_info), 'site-packages')


def assert_vendored():


    force = os.environ.get('VEE_FORCE_BOOTSTRAP_VENDORED')

    missing_something = force
    if not force:
        for name in vendored_packages:
            path = os.path.join(vendor_path, name)
            if not os.path.exists(path) and not os.path.exists(path + '.py'):
                missing_something = True
                break

    if missing_something:

        pip = os.path.join(vendor_prefix, 'bin', 'pip')

        # Get pip.
        if force or not os.path.exists(pip):
            get_pip = os.path.abspath(os.path.join(__file__, '..', 'get-pip.py'))
            subprocess.check_call([sys.executable, get_pip, '-I', '--prefix', vendor_prefix])

        subprocess.check_call([sys.executable,
            pip,
            'install',
            '--ignore-installed',
            '--upgrade',
            '--prefix', vendor_prefix,
        ] + vendored_packages)

    return vendor_path


def bootstrap_vendored():

    prefix = assert_vendored()

    # Force our vendored packages to the front of the path.
    if prefix not in sys.path:
        sys.path.insert(0, prefix)

    import pkg_resources

    # Make our vendored packages availible to provide entry_points, etc..
    if prefix not in pkg_resources.working_set.entries:
        pkg_resources.working_set.add_entry(prefix)


def bootstrap_environ(environ=None):

    environ = environ or os.environ

    try:
        py_path = environ['PYTHONPATH'].split(':')
    except KeyError:
        environ['PYTHONPATH'] = vendor_path
    else:
        if vendor_path not in py_path:
            py_path.insert(0, vendor_path)
            environ['PYTHONPATH'] = ':'.join(py_path)


def bootstrap_entrypoints():

    import pkg_resources

    # See if we are already registered.
    req = pkg_resources.Requirement.parse('vee')
    dist = pkg_resources.working_set.find(req)
    if dist is not None:
        return

    # Make a dummy metadata provider (which looks in our package for metadata),
    # and a dummy distribution (which lives wherever it does on dist).
    class Provider(pkg_resources.DefaultProvider):
        egg_info = os.path.abspath(os.path.join(__file__, '..', '..', '_egg-info'))
    dummy = pkg_resources.Distribution(
        project_name='vee',
        version='99.99.99',
        metadata=Provider('vee'),
        location=os.path.abspath(os.path.join(__file__, '..', '..', '..')),
    )
    pkg_resources.working_set.add(dummy)


def bootstrap():
    bootstrap_vendored()
    bootstrap_environ()
    bootstrap_entrypoints()

