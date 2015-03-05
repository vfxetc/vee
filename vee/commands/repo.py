import sqlite3

from vee.cli import style_error, style_warning, style_note
from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.exceptions import CliException
from vee.home import PRIMARY_REPO


@command(
    help='manage remote repos',
    usage='vee repo (add|set|delete|list) [OPTIONS]'
)
def repo(args):
    # Never goes here.
    pass


@repo.subcommand()
def list(args):
    home = args.assert_home()
    rows = list(home.db.execute('SELECT * FROM repositories'))
    if not rows:
        print style_warning('No repositories.')
        return
    max_len = max(len(row['name']) for row in rows)
    for row in rows:
        print style_note(row['name'], row['url'], '--default' if row['is_default'] else '')


@repo.subcommand(
    argument('name'),
)
def delete(args):
    home = args.assert_home()
    cur = home.db.execute('DELETE FROM repositories WHERE name = ?', [args.name])
    if not cur.rowcount:
        print style_error('No %r repository.' % args.name)


@repo.subcommand(
    argument('--default', action='store_true', help='with --add/--set: set to be default'),
    argument('--branch', help='with --add/--set: sets git branch to track'),
    argument('name'),
    argument('url', nargs='?'),
)
def set(args):
    return add(args, is_set=True)

@repo.subcommand(
    argument('--default', action='store_true', help='with --add/--set: set to be default'),
    argument('--branch', help='with --add/--set: sets git branch to track'),
    argument('name'),
    argument('url'),
)
def add(args, is_set=False):

    is_add = not is_set

    home = args.assert_home()

    con = home.db.connect()
    row = con.execute('SELECT id FROM repositories WHERE name = ?', [args.name]).fetchone()

    if is_add and row:
        raise CliException('repo %s already exists' % args.name)

    if is_set:
        if not (args.url or args.default):
            raise CliException('--default or url is required')
        if not row:
            raise CliException('repo %s does not exist' % args.name)

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

    if args.url:
        repo = home.get_env_repo(args.name)
        repo.clone_if_not_exists()
