from __future__ import print_function

import os
import sys

from vee.cli import style, style_note, style_warning
from vee.commands.main import command, argument
from vee.subproc import call, which


def parse_version(x):
    parts = x.split('.')
    for i, x in enumerate(parts):
        try:
            parts[i] = int(x)
        except ValueError:
            pass
    return tuple(parts)


@command(
    argument('--ping', action='store_true', help='print "pong", and exit'),
    argument('--version', action='store_true', help='print VEE\'s version, and exit'),
    argument('--revision', action='store_true', help='print VEE\'s revision, and exit'),
    help='perform a self-check',
    usage='vee doctor [--ping,--version,--revision]',
    group='setup',
)
def doctor(args):
    """Perform self-checks to make sure VEE is OK."""

    if args.ping:
        print('pong')
        return

    import vee.__about__ as about

    if args.version:
        print(about.__version__ + ('+' + about.__revision__ if args.revision else ''))
        return
    if args.revision:
        print(about.__revision__)
        return

    print(style_note('==> core'))
    print(style_note('version:', repr(about.__version__)))
    print(style_note('revision:', repr(about.__revision__)))
    print(style_note('package:', repr(os.path.abspath(os.path.join(__file__, '..', '..')))))

    res = 0

    def find_command(name):
        path = which(name)
        if path:
            print(style_note(repr(path) + ":"))
            return 0
        else:
            print(style(name + ":", 'yellow'), None)
            return 1

    print(style_note('==> dependencies'))
    for name, expected_version, in [
        ('setuptools', '36.0.0'),
        ('pip', '20.0.0'),
        ('virtualenv', '15.0.0'),
        ('packaging', '16.0'),
        ('wheel', '0.29.0'),
    ]:

        try:
            module = __import__(name)
        except ImportError as e:
            print(style(name + ":", 'yellow'), None)
            res = 2
            continue

        actual_version = module.__version__
        if parse_version(expected_version) <= parse_version(actual_version):
            print(style_note(name + ":", "{!r} >= {!r}".format(actual_version, expected_version)))
        else:
            print(style(name + ":", 'yellow'), "{!r} < {!r} (from {})".format(actual_version, expected_version, module.__file__))
            res = 2

    print(style_note('==> executables'))
    print(style_note('python:', sys.executable))
    res = find_command('git') or res
    if sys.platform == 'darwin':
        res = find_command('install_name_tool') or res
    if sys.platform.startswith('linux'):
        res = find_command('patchelf') or res

    print(style_note('==> runtime'))
    print(style_note('sys.real_prefix:', repr(getattr(sys, 'real_prefix', None))))
    print(style_note('sys.base_prefix:', repr(getattr(sys, 'base_prefix', None))))
    print(style_note('sys.prefix:', repr(sys.prefix)))

    print(style_note('==> config'))
    home = args.assert_home()
    print(style_note('home:', repr(home.root)))
    try:
        repo = home.get_repo()
        print(style_note('repo:', repr(repo.name), repr(repo.remote_url)))
    except ValueError:
        print(style("repo:", 'yellow'), None)
        res = res or 3

    print(style_note('==> summary'))
    if not res:
        print(style('Everything looks OK.', 'green'))
    else:
        print(style('Something looks wrong.', 'yellow'))

    return res

