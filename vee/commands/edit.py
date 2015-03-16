import os
import shlex

from vee.cli import style, style_error, style_note
from vee.commands.main import command, argument
from vee.git import GitRepo, normalize_git_url
from vee.subproc import call


@command(
    argument('-r', '--repo', nargs='?'),
)
def edit(args):

    home = args.assert_home()
    env_repo = home.get_env_repo(args.repo)

    cmd = []
    cmd.extend(shlex.split(os.environ['EDITOR']))
    cmd.append(os.path.join(env_repo.work_tree, 'requirements.txt'))
    os.execvp(cmd[0], cmd)
