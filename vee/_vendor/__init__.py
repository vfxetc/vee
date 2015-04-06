import os
import sys


# Force our vendored packages to the front of the path.
vendor_path = os.path.abspath(os.path.join(__file__, '..'))
if vendor_path not in sys.path:
    sys.path.append(vendor_path)


import pkg_resources


# Make our vendored packages availible to provide entry_points, etc..
if vendor_path not in pkg_resources.working_set.entries:
    pkg_resources.working_set.add_entry(vendor_path)


def bootstrap_environ(environ):
    try:
        py_path = environ['PYTHONPATH'].split(':')
    except KeyError:
        environ['PYTHONPATH'] = vendor_path
    else:
        if vendor_path not in py_path:
            py_path.append(vendor_path)
            environ['PYTHONPATH'] = ':'.join(py_path)


# Also provide these packages to later environments.
original_environ = os.environ.copy()
bootstrap_environ(os.environ)

