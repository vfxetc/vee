#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import traceback


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
        print(red("Error:") + " vee can't bootstrap.", file=sys.stderr)
        print(e, file=sys.stderr)
        exit(2)

else:
    bootstrapped = None


try:
    from vee.commands.main import main

except ImportError as e:
    print(red("Error:") + " vee's install is broken.", file=sys.stderr)
    traceback.print_exc()
    if bootstrapped:
        print('Bootstrap found:', bootstrapped, file=sys.stderr)
    exit(1)


exit(main(as_main=True) or 0)
