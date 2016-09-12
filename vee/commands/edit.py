import os
import shlex

from vee.cli import style, style_error, style_note
from vee.commands.main import command, argument
from vee.git import GitRepo, normalize_git_url
from vee.subproc import call
from vee import log


@command(
    argument('-r', '--repo', nargs='?'),
    help='open requirements.txt in $EDITOR',
    group='development',
)
def edit(args):

    home = args.assert_home()
    env_repo = home.get_env_repo(args.repo)

    cmd = []
    cmd.extend(shlex.split(os.environ.get('EDITOR', 'vim')))
    cmd.append(os.path.join(env_repo.work_tree, 'requirements.txt'))

    log.debug(cmd, verbosity=1)

    os.execvp(cmd[0], cmd)
