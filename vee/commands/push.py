import re

from vee.cli import style, style_error, style_note
from vee.commands.main import command, argument
from vee.git import GitRepo, normalize_git_url


@command(
    argument('-r', '--repo'),
    help='push changes to environment repo',
    group='development',
)
def push(args):
    home = args.assert_home()

    # TODO: push all tools, or at least check them.

    env_repo = home.get_env_repo(args.repo)
    env_repo.git('push')
