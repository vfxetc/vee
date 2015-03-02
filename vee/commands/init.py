from vee.commands.main import command, argument
from vee.home import PRIMARY_REPO
from vee.utils import style


@command(
    argument('--name', default=PRIMARY_REPO, help='name for new repository'),
    argument('url', nargs='?', help='URL of new repository'),
    help='initialize VEE\'s home',
    usage='vee init URL',
)
def init(args):

    home = args.assert_home()

    print style('Initializing "%s"' % args.name, 'blue', bold=True), home.root
    home.init(name=args.name, url=args.url)
    
