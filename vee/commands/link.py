from vee.commands.main import command, argument
from vee.environment import Environment
from vee.requirement import Requirement
from vee.utils import colour
from vee.exceptions import CliException, AlreadyInstalled


@command(
    argument('--raw', action='store_true', help='package is directory, not a requirement'),
    argument('environment'),
    argument('specification', nargs='...'),
    help='link a package',
    usage='vee link [--raw] ENVIRONMENT SPECIFICATION',
)
def link(args):

    args.assert_home()

    env = Environment(args.environment, home=args.home)

    if args.raw:
        for dir_ in args.package:
            print colour('Linking', 'blue', bright=True), colour(dir_, 'black', reset=True)
            env.link_directory(dir_)
        return

    for line in open(args.specification[0]):

        line = line.strip()
        if not line or line.startswith('#'):
            continue

        req = Requirement(line, home=args.home)
        try:
            req.install()
        except AlreadyInstalled:
            pass
        
        print colour('Linking', 'blue', bright=True), colour(str(req), 'black', reset=True)

        req.manager.link(env)
        


