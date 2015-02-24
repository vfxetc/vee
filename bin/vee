#!/usr/bin/env python

import os
import sys


def ANSI(*args):
    return ''.join('\x1b[' + str(x) for x in args)
def SGR(*args):
    return ''.join(ANSI(str(x) + 'm') for x in args)
red = lambda x: SGR(1, 31) + x + SGR(0)


try:
    from vee.commands.main import main

except ImportError as e:
    here = os.path.abspath(os.path.join(__file__, '..', '..'))
    for path in (here, os.path.join(here, 'lib/python2.7/site-packages')):
        init_py = os.path.join(path, 'vee', '__init__.py')
        if os.path.exists(init_py):
            bootstrapped = path
            sys.path.append(path)
            break
    else:
        print >> sys.stderr, red("Error:") + " vee can't bootstrap."
        print >> sys.stderr, e
        exit(2)

else:
    bootstrapped = None


try:
    from vee.commands.main import main

except ImportError as e:
    print >> sys.stderr, red("Error:") + " vee's install is broken."
    print >> sys.stderr, e
    if bootstrapped:
        print >> sys.stderr, 'Bootstrap found:', bootstrapped
    exit(1)


# Auto-detect the home.
if os.environ.get('VEE') is None:
    root = os.path.dirname(__file__)
    while len(root) > 1:
        if os.path.exists(os.path.join(root, 'vee-index.db')):
            os.environ['VEE'] = root
            break
        root = os.path.dirname(root)


exit(main(as_main=True) or 0)
