from vee.commands.main import command, argument, group
from vee.environment import Environment


@command(
    group(
        argument('--get', action='store_true', help='get given keys (default)'),
        argument('--list', action='store_true', help='list all variables set'),
        argument('--set', action='store_true', help='set key-value pairs'),
        argument('--delete', action='store_true', help='delete given keys'),
        argument('--clear', action='store_true', help='clear all config'),
        exclusive=True,
    ),
    argument('args', nargs='...'),
    help='manage the configuration',
    # usage='vee env ENVIRONMENT',
)
def config(args):

    args.assert_home()
    config = args.home.config

    if args.list:
        for k, v in sorted(config.iteritems()):
            print '%s=%s' % (k, v)
        return

    if args.set:
        if len(args.args) % 2:
            raise CliException('--set requires even number of arguments')
        for i in xrange(0, len(args.args), 2):
            config[args.args[i]] = args.args[i + 1]
        return

    if args.delete:
        for k in args.args:
            del config[k]
    
    if args.clear:
        config.clear()
    
    for k in args.args:
        print config[k]
