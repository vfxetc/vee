import re

from vee.cli import style, style_error, style_note
from vee.commands.main import command, argument
from vee.git import GitRepo, normalize_git_url


@command()
def push(args):
    home = args.assert_home()
    env_repo = home.get_env_repo()
    env_repo.git('push')
