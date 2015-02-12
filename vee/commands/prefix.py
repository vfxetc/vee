from vee.commands.main import command, argument
from vee.environment import Environment


@command(
    argument('--raw', action='store_true', help='package is directory, not a requirement'),
    argument('environment'),
    argument('specification', nargs='...'),
    help='get the prefix of an environment',
    usage='vee prefix ENVIRONMENT',
)
def prefix(args):
    args.assert_home()
    env = Environment(args.environment, home=args.home)
    print env.root

