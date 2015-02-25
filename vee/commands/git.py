from vee.commands.main import command, argument
from vee.exceptions import CliException
from vee.git import GitRepo
from vee.utils import makedirs


@command(
    help='run a git command in the repo',
    parse_known_args=True,
)
def git(args, *command):
    args.assert_home()
    makedirs(args.home.repo.work_tree)
    args.home.repo._call(*command, silent=True)
