from vee.commands.main import command, argument
from vee.home import PRIMARY_REPO
from vee.requirement import Requirement
from vee.utils import style


@command(
    argument('--name', default=PRIMARY_REPO, help='name for new repository'),
    argument('--repo', help='URL of new repository'),
    argument('--umask', help='default umask for all files'),
    argument('--chgrp', help='default group for all files'),
    help='initialize VEE\'s home',
    usage='vee init',
)
def init(args):

    home = args.assert_home()

    print style('Initializing home', 'blue', bold=True), style(home.root)

    home.makedirs()

    config = home.config

    config.setdefault('repo.default.name', args.name)

    if args.umask:
        config['os.umask'] = args.umask
    else:
        config.setdefault('os.umask', '0002')

    if args.chgrp:
        config['os.chgrp'] = args.chgrp

    if args.repo:
        config['repo.%s.url' % args.name] = args.repo

