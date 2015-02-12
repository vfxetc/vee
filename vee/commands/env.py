from vee.commands.main import command, argument
from vee.environment import Environment


@command(
    argument('environment'),
    help='dump environment variables for this environment',
    usage='vee env ENVIRONMENT',
)
def env(args):
    args.assert_home()
    env = Environment(args.environment, home=args.home)
    for k, v in sorted(env.get_environ().iteritems()):
        print 'export %s="%s"' % (k, v)

