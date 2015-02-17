from vee.commands.main import command, argument
from vee.environment import Environment


@command(
    argument('environment'),
    help='get the prefix of an environment',
    usage='vee prefix ENVIRONMENT',
)
def prefix(args):
    args.assert_home()
    env = Environment(args.environment, home=args.home)
    print env.root

