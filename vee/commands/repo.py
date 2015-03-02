import sqlite3


from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.home import PRIMARY_REPO
from vee.exceptions import CliException
from vee.utils import style_error

@command(
    group(
        argument('--add', action='store_const', dest='action', const='add', help='add a new repo'),
        argument('--set', action='store_const', dest='action', const='set', help='change an existing repo'),
        argument('--delete', action='store_const', dest='action', const='delete', help='delete a repo'),
        argument('--list', action='store_const', dest='action', const='list', help='list all repos'),
        exclusive=True,
    ),
    argument('--default', action='store_true', help='with --add/--set: set to be default'),
    argument('--branch', help='with --add/--set: sets git branch to track'),
    argument('name', nargs='?'),
    argument('url', nargs='?'),
    help='manage remote repos',
)
def repo(args):

    home = args.assert_home()
    config = home.config

    if args.action in ('list', None):
        rows = list(home.db.execute('SELECT * FROM repositories'))
        max_len = max(len(row['name']) for row in rows)
        for row in rows:
            print '%d %s %s%s' % (row['id'], '%%%ds' % max_len % row['name'], row['url'],
                ' --default' if row['is_default'] else '',
            )
        return

    if not args.name:
        raise CliException('name is required for --%s' % args.action)

    if args.action == 'delete':
        home.db.execute('DELETE FROM repositories WHERE name = ?', [args.name])
        return

    # Only --add and --set from here.

    con = home.db.connect()
    row = con.execute('SELECT id FROM repositories WHERE name = ?', [args.name]).fetchone()

    if args.action == 'add':
        if not args.url:
            raise CliException('url is required for --add')
        if row:
            raise CliException('repo %s already exists' % args.name)
    elif args.action == 'set':
        if not (args.url or args.default):
            raise CliException('--default or url is required for --set')
        if not row:
            raise CliException('repo %s does not exist' % args.name)
    else:
        # Should never get here.
        raise CliException('unknown action --%s' % args.action)

    data = {}
    for attr, key in (
        ('name', None),
        ('url', None),
        ('branch', None),
        ('default', 'is_default'),
    ):
        value = getattr(args, attr)
        if value is not None:
            data[key or attr] = value

    if row:
        home.db.update('repositories', data, where={'id': row['id']})
    else:
        home.db.insert('repositories', data)
