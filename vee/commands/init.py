from vee.cli import style
from vee.commands.main import command, argument
from vee.home import PRIMARY_REPO


@command(
    argument('--name', default=PRIMARY_REPO, help='name for new repository'),
    argument('url', nargs='?', help='URL of new repository'),
    help='initialize VEE\'s home',
    usage='vee init URL',
)
def init(args):
    args.home.init(name=args.name, url=args.url)

