from vee import log
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

        vee init git@github.com:vfxetc/vee-repo primary

    This is the same as:

        vee init
        vee repo clone git@github.com:vfxetc/vee-repo primary


    """

    try:
        args.home.init()
        log.info('Initialized %s' % args.home.root)
    except ValueError:
        log.error('Home already exists.')
        if args.url:
            log.info('Create a new repository via:')
            log.info('\tvee repo clone --default %s %s' % (args.url, args.name or ''))
        return

    if args.url:
        repo = args.home.create_env_repo(url=args.url, name=args.name)
        log.info('Created repo %s at %s' % (repo.name, repo.work_tree))

