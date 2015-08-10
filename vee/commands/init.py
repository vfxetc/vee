from vee.cli import style, style_error
from vee.commands.main import command, argument
from vee.home import PRIMARY_REPO


@command(
    argument('--name', help='name for new repository'),
    argument('url', nargs='?', help='URL of new repository to clone'),
    help='initialize VEE\'s home',
    usage='vee init URL',
)
def init(args):

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

