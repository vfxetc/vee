from textwrap import dedent
import os
import ssl
import subprocess
import sys
import urllib

from vee.utils import makedirs, find_home


vee_home = find_home(default_here=True)
vendored_packages = ['setuptools', 'wheel', 'packaging', 'virtualenv', 'urllib3']
vendor_prefix = os.environ.get('VEE_VENDOR', '').strip() or os.path.join(vee_home, 'vendor')
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
            subprocess.check_call([sys.executable, get_pip, '-I', '--prefix', vendor_prefix], stdout=sys.stderr)

        # We really need to jump through a hoop here, because sometimes
        # the Python shipped with macOS has a pip egg, which gets priority
        # on sys.path. See <http://mikeboers.com/blog/2014/05/23/where-does-the-sys-path-start>.
        # So here we are mimicking what the `pip.__main__` module does to force
        # our pip to be the one that is run.
        subprocess.check_call([

            'python', '-c', dedent('''

                import sys
                sys.path.insert(0, {!r})

                from pip._internal import main as _main
                sys.exit(_main())

            '''.format(vendor_path)),

            'install',
            '--upgrade',
            '--ignore-installed',
            '--cache-dir', os.path.join(vee_home, 'cache', 'pip'),
            '--prefix', vendor_prefix,

        ] + vendored_packages, stdout=sys.stderr)


def bootstrap_vendored():

    assert_vendored()

    # Force our vendored packages to the front of the path.
    # We're super agressive because macOS may have shipped with eggs which
    # land in front.
    sys.path.insert(0, vendor_path)

    import pkg_resources

    # Make our vendored packages availible to provide entry_points, etc..
    if vendor_path not in pkg_resources.working_set.entries:
        pkg_resources.working_set.add_entry(vendor_path)


def bootstrap_openssl():

    # NOTE: The logic here is lifted entirely from pip;
    # see https://github.com/pypa/pip/commit/9c037803197b05bb722223c2f5deffcbb7f4b0c4

    # We want to inject the use of SecureTransport as early as possible so that any
    # references or sessions or what have you are ensured to have it, however we
    # only want to do this in the case that we're running on macOS and the linked
    # OpenSSL is too old to handle TLSv1.2
    if sys.platform == "darwin" and ssl.OPENSSL_VERSION_NUMBER < 0x1000100f:  # OpenSSL 1.0.1
        import urllib3.contrib.securetransport
        urllib3.contrib.securetransport.inject_into_urllib3()


def bootstrap_environ(environ=None):

    environ = environ or os.environ

    #environ['VEE_VENDOR'] = vendor_prefix

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
    bootstrap_openssl()
    bootstrap_environ()
    bootstrap_entrypoints()

