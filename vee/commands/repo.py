from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.home import PRIMARY_REPO


@command(
    group(
        argument('--add', action='store_const', dest='action', const='add', help='add a new repo'),
        argument('--delete', action='store_const', dest='action', const='delete', help='delete a repo'),
        argument('--list', action='store_const', dest='action', const='list', help='list all repos'),
        exclusive=True,
    ),
    argument('--default', action='store_true', help='with --add: set to be default'),
    argument('--remote', help='with --add: sets git remote name'),
    argument('--parent', help='with --add: inherits from another VEE'),
    argument('name', nargs='?'),
    argument('url', nargs='?'),
    help='manage remote repos',
)
def repo(args):

    home = args.assert_home()
    config = home.config

    if args.action in ('list', None):
        default = config.get('repo.default.name', PRIMARY_REPO)
        for key, url in sorted(config.iteritems(glob='repo.*.url')):
            name = key.split('.')[1]
            parent = config.get('repo.%s.parent' % name)
            print '%s %s%s%s' % (name, url,
                ' --default' if name == default else '',
                ' --parent %s' % parent if parent else '',
            )
        return

    if not args.name:
        raise CliException('name is required for --%s' % args.action)

    if args.action == 'delete':
        del config['repo.%s.url' % args.name]
        return

    if args.action == 'add':
        if not (args.url or args.default or args.parent):
            raise CliException('--default, --parent, or url is required for --%s' % args.action)
        if args.url:
            config['repo.%s.url' % args.name] = args.url
        if args.parent:
            config['repo.%s.parent' % args.name] = args.parent
        if args.remote:
            config['repo.%s.remote' % args.name] = args.remote
        if args.default:
            config['repo.default.name'] = args.name
        return

