from vee.cli import style, style_error
from vee.commands.main import command, argument
from vee.home import PRIMARY_REPO


@command(
    argument('url', nargs='?', help='URL of new repository to clone'),
    argument('name', nargs='?', help='name for new repository'),
    help='initialize VEE\'s home',
    usage='vee init URL',
    group='setup',
)
def init(args):
    """Initialize the structures on disk before any other commands, and
    optionally setup the first environment repository.

    E.g.:

        vee init git@git.westernx:westernx/vee-repo primary

    This is the same as:

        vee init
        vee repo clone git@git.westernx:westernx/vee-repo primary


    """

    try:
        args.home.init()
        print 'Initialized %s' % args.home.root
    except ValueError:
        print style_error('Home already exists.')
        if args.url:
            print 'Create a new repository via:'
            print '\tvee repo clone --default %s %s' % (args.url, args.name or '')
        return

    if args.url:
        env_repo = args.home.create_env_repo(url=args.url, name=args.name)
        print 'Created repo %s at %s' % (env_repo.name, env_repo.work_tree)

