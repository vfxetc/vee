import sqlite3

from vee.cli import style_error, style_warning, style_note
from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.exceptions import CliException
from vee.home import PRIMARY_REPO


@command(
    help='manage remote repos',
    usage='vee repo (clone|set|delete|list) [OPTIONS]'
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
    argument('--default', action='store_true', help='this repo is the default'),
    argument('--remote', help='git remote to track'),
    argument('--branch', help='git branch to track'),
    argument('--url', help='remote url'),
    argument('name'),
)
def set(args):
    home = args.assert_home()
    if not (args.default or args.remote or args.branch or args.url):
        raise CliException('please specify something to set')
    home.update_env_repo(
        name=args.name,
        url=args.url,
        remote=args.remote,
        branch=args.branch,
        is_default=args.default,
    )


@repo.subcommand(
    argument('--default', action='store_true', help='this repo is the default'),
    argument('--remote', help='git remote to track', default='origin'),
    argument('--branch', help='git branch to track', default='master'),
    argument('url'),
    argument('name', nargs='?'),
)
def clone(args, is_set=False):
    home = args.assert_home()
    args.name = args.name or re.sub(r'\.git$', '', os.path.basename(args.url))
    home.clone_env_repo(
        name=args.name,
        url=args.url,
        remote=args.remote,
        branch=args.branch,
        is_default=args.default,
    )


