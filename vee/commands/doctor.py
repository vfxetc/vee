import os
import sys

from vee.cli import style, style_note, style_warning
from vee.commands.main import command, argument
from vee.subproc import call, which


@command(
    argument('--ping', action='store_true', help='print "pong"'),
    argument('--version', action='store_true', help='print version'),
    argument('--revision', action='store_true', help='print revision'),
    help='perform a self-check',
)
def doctor(args):

    if args.ping:
        print 'pong'
        return

    import vee.__about__ as about

    if args.version:
        print about.__version__ + ('+' + about.__revision__ if args.revision else '')
        return
    if args.revision:
        print about.__revision__
        return

    print style_note('==> VEE')
    print style_note('version:', about.__version__)
    print style_note('revision:', about.__revision__)
    print style_note('package:', os.path.abspath(os.path.join(__file__, '..', '..')))

    res = 0

    def find_command(name, warn=False):
        path = which(name)
        if path:
            print style_note('%s:' % name, path)
        else:
            if warn:
                print style_warning('cannot find %s' % name)
            else:
                print style_error('cannot find %s' % name)
                return 1

    print style_note('==> executables')
    print style_note('python:', sys.executable)
    res = find_command('git') and res
    if sys.platform == 'darwin':
        res = find_command('install_name_tool') and res
    if sys.platform.startswith('linux'):
        res = find_command('chrpath', warn=True) and res

    print style_note('==> configuration')
    home = args.assert_home()
    print style_note('home:', home.root)

    try:
        repo = home.get_env_repo()
    except ValueError:
        print style_warning('no default repo.', 'Use `vee repo add --default URL`.')
        return
    print style_note('repo:', repo.name, repo.remote_url)

    print style_note('==> summary')
    if not res:
        print style('Everything looks OK', 'green')
    else:
        print style('Something may be wrong', 'yellow')

    return res

