from vee.commands.main import command, argument
from vee.exceptions import CliException
from vee.git import GitRepo
from vee.utils import makedirs


@command(
    argument('-r', '--repo', help='which repo to use'),
    help='run a git command in the repo',
    parse_known_args=True,
)
def git(args, *command):

    home = args.assert_home()
    repo = home.get_env_repo(args.repo)

    makedirs(repo.work_tree)
    repo.git(*command, silent=True)

