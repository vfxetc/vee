
from vee.cli import style_error
from vee.commands.main import command, argument
from vee.subproc import call
from vee.utils import makedirs


@command(
    argument('-r', '--repo', help='which repo to use'),
    argument('--stree', action='store_true', help='launch SourceTree'),
    help='run a git command in a repository',
    parse_known_args=True,
)
def git(args, *command):

    home = args.assert_home()
    repo = home.get_env_repo(args.repo)

    if args.stree:
        call(['stree', repo.work_tree])
        return

    if not command:
        print style_error('please provide a git command')
        return 1
    
    makedirs(repo.work_tree)
    repo.git(*command, verbosity=0, indent=False)
