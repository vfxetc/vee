import sqlite3


from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.home import PRIMARY_REPO
from vee.exceptions import CliException
from vee.utils import style_error

@command(
    group(
        argument('--add', action='store_const', dest='action', const='add', help='add a new repo'),
        argument('--delete', action='store_const', dest='action', const='delete', help='delete a repo'),
        argument('--list', action='store_const', dest='action', const='list', help='list all repos'),
        exclusive=True,
    ),
    argument('--default', action='store_true', help='with --add: set to be default'),
    argument('--remote', help='with --add: sets git remote name'),
    argument('--branch', help='with --add: sets git branch name'),
    argument('--parent', help='with --add: inherits from another VEE'),
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
            print '%d %s %s%s%s' % (row['id'], '%%%ds' % max_len % row['name'], row['url'],
                ' --default' if row['is_default'] else '',
                ' --parent %s' % row['parent_path'] if row['parent_path'] else '',
            )
        return

    if not args.name:
        raise CliException('name is required for --%s' % args.action)

    if args.action == 'delete':
        home.db.execute('DELETE FROM repositories WHERE name = ?', [args.name])
        return

    if args.action == 'add':

        if not (args.url or args.default or args.parent):
            raise CliException('--default, --parent, or url is required for --%s' % args.action)


        data = {}
        for attr, key in (
            ('name', None),
            ('url', None),
            ('parent', 'parent_path'),
            ('remote', None),
            ('branch', None),
            ('default', 'is_default'),
        ):
            value = getattr(args, attr)
            if value is not None:
                data[key or attr] = value

        con = home.db.connect()
        row = con.execute('SELECT id FROM repositories WHERE name = ?', [args.name]).fetchone()
        if row:
            home.db.update('repositories', data, where={'id': row['id']})
        else:
            home.db.insert('repositories', data)
