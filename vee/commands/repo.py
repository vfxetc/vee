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
       vee repo init OPTIONS NAME
   or: vee repo clone OPTIONS URL [NAME]
   or: vee repo set OPTIONS NAME
   or: vee repo delete NAME
   or: vee repo list
""".strip()
)
def repo(args):
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
        print style_error('No %r repository.' % args.name)


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
        print style_warning('No repositories.')
        return
    max_len = max(len(row['name']) for row in rows)
    for row in rows:
        env_repo = EnvironmentRepo(row, home=home)
        if env_repo.exists:
            print style_note(
                env_repo.name,
                '%s/%s' % (env_repo.remote_name, env_repo.branch_name),
                env_repo.remotes().get(env_repo.remote_name, '') + 
                ' --default' if row['is_default'] else '',
            )


@repo.subcommand(
    argument('-r', '--repo', help='which repo to use'),
    help='run a git command in a repository',
    parse_known_args=True,
)
def git(args, *command):

    if not command:
        print style_error('please provide a git command')
        return 1
    
    home = args.assert_home()
    repo = home.get_env_repo(args.repo)

    makedirs(repo.work_tree)
    repo.git(*command, silent=True)



