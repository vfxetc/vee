import sqlite3

from vee.cli import style_error, style_warning, style_note
from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.environmentrepo import EnvironmentRepo
from vee.home import PRIMARY_REPO
from vee.utils import makedirs


@command(
    help='manage environment repos',
    usage="""
       vee repo init NAME
   or: vee repo add PATH [NAME]
   or: vee repo clone URL [NAME]
   or: vee repo set NAME
   or: vee repo delete NAME
   or: vee repo list
""".strip(),
    group='setup',
)
def repo(args):
    """Manipulate environment repositories,
    e.g.::

        # Start a new repo.
        $ vee repo init example

        # Add a new repo, and make it the default.
        $ vee repo clone --default git@github.com:example/myrepo

        # Change a repo's url and branch
        $ vee repo set --branch unstable myrepo

        # Delete a repo.
        $ vee repo delete myrepo

        # List all repos.
        $ vee repo list

    """
    # Never goes here.
    pass


@repo.subcommand(
    argument('--default', action='store_true', help='this repo is the default'),
    argument('--remote', help='git remote to track', default='origin'),
    argument('--branch', help='git branch to track', default='master'),
    argument('name', nargs='?'),
    help='create a blank repository'
)
def init(args, is_set=False):
    home = args.assert_home()
    home.create_env_repo(
        name=args.name,
        url=None,
        remote=args.remote,
        branch=args.branch,
        is_default=args.default,
    )


@repo.subcommand(
    argument('--default', action='store_true', help='this repo is the default'),
    argument('--remote', help='git remote to track', default='origin'),
    argument('--branch', help='git branch to track', default='master'),
    argument('path'),
    argument('name', nargs='?'),
    help='add an existing repository clone'
)
def add(args, is_set=False):
    home = args.assert_home()
    home.create_env_repo(
        name=args.name,
        path=args.path,
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
    help='clone a remote repository'
)
def clone(args, is_set=False):
    home = args.assert_home()
    home.create_env_repo(
        name=args.name,
        url=args.url,
        remote=args.remote,
        branch=args.branch,
        is_default=args.default,
    )


@repo.subcommand(
    argument('name'),
)
def delete(args):
    home = args.assert_home()
    cur = home.db.execute('DELETE FROM repositories WHERE name = ?', [args.name])
    if not cur.rowcount:
        log.error('No %r repository.' % args.name)


@repo.subcommand(
    argument('--default', action='store_true', help='this repo is the default'),
    argument('--remote', help='git remote to track'),
    argument('--branch', help='git branch to track'),
    argument('--url', help='remote url (set via `git remote`)'),
    argument('name'),
    help='set options on an existing repository'
)
def set(args):
    home = args.assert_home()
    if not (args.default or args.remote or args.branch or args.url):
        raise ValueError('please specify something to set')
    home.update_env_repo(
        name=args.name,
        url=args.url,
        remote=args.remote,
        branch=args.branch,
        is_default=args.default,
    )


@repo.subcommand(
    name='list',
    help='list local repositories'
)
def list_(args):
    home = args.assert_home()
    rows = list(home.db.execute('SELECT * FROM repositories'))
    if not rows:
        log.warning('No repositories.')
        return
    max_len = max(len(row['name']) for row in rows)
    for row in rows:
        env_repo = EnvironmentRepo(row, home=home)
        if env_repo.exists:
            log.info(style_note(
                env_repo.name,
                '%s/%s' % (env_repo.remote_name, env_repo.branch_name),
                env_repo.remotes().get(env_repo.remote_name, '') + 
                ' --default' if row['is_default'] else '',
            ))





