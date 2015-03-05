import re

from vee.commands.main import command, argument
from vee.exceptions import CliException
from vee.git import GitRepo, normalize_git_url
from vee.utils import style, style_error, style_note


@command()
def push(args):
    home = args.assert_home()
    req_repo = home.get_repo()
    req_repo.git('push')
