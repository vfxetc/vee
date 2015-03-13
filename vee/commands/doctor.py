from vee.cli import style, style_note, style_warning
from vee.commands.main import command, argument


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

    if args.version:
        import vee.__about__ as about
        print about.__version__ + ('+' + about.__revision__ if args.revision else '')
        return
    if args.revision:
        import vee.__about__ as about
        print about.__revision__
        return

    home = args.assert_home()

    print style_note('Home:', home.root)

    try:
        repo = home.get_env_repo()
    except ValueError:
        print style_warning('No default repo.', 'Use `vee repo add --default URL`.')
        return

    print style_note('Default repo:', repo.name, repo.remote_url)

    print style_warning('Doctor is incomplete.', 'There are many things we aren\'t testing yet.')
    print style('OK', 'green', bold=True)

