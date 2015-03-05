import re

from vee.cli import style, style_error, style_note
from vee.commands.main import command, argument
from vee.exceptions import CliException
from vee.git import GitRepo, normalize_git_url


@command()
def push(args):
    home = args.assert_home()
    req_repo = home.get_repo()
    req_repo.git('push')
