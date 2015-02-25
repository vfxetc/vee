from vee.commands.main import command, argument, group
from vee.environment import Environment


@command(
    group(
        argument('--add', action='store_const', dest='action', const='add', help='add a new repo'),
        argument('--set-default', action='store_const', dest='action', const='set-default', help='set a repo to be the default'),
        argument('--delete', action='store_const', dest='action', const='delete', help='delete a repo'),
        argument('--list', action='store_const', dest='action', const='list', help='list all repos'),
        exclusive=True,
    ),
    argument('name', nargs='?'),
    argument('url', nargs='?'),
    help='manage remote repos',
)
def repo(args):

    home = args.assert_home()
    config = home.config

    if args.action in ('list', None):
        default = config.get('repo.default.name', 'master')
        for key, url in sorted(config.iteritems(glob='repo.*.url')):
            name = key.split('.')[1]
            print '%s %s%s' % (name, url, ' (default)' if name == default else ' ')
        return

    if not args.name:
        raise CliException('name is required for --%s' % args.action)

    if args.action == 'delete':
        del config['repo.%s.url' % args.name]
        return

    if args.action == 'set-default':
        config['repo.default.name'] = args.name
        return

    if not args.url:
        raise CliException('url is required for --%s' % args.action)

    if args.action == 'add':
        config['repo.%s.url' % args.name] = args.url
        return

