
from vee.cli import style_error
from vee.commands.main import command, argument
from vee.subproc import call
from vee.utils import makedirs


@command(
    argument('-r', '--repo', help='which repo to use'),
    argument('--stree', action='store_true', help='launch SourceTree'),
    help='run a git command in a repository',
    parse_known_args=True,
    group='plumbing',
    usage='vee git [-r REPO] COMMAND+',
)
def git(args, *command):
    """Run a ``git`` command on a environment repository's git repository.
    (Sorry for the name collision.)

    e.g.::

        $ vee git -r primary status
        On branch master
        Your branch is behind 'origin/master' by 1 commit, and can be fast-forwarded.
          (use "git pull" to update your local branch)
        nothing to commit, working directory clean

    """

    home = args.assert_home()
    repo = home.get_env_repo(args.repo)

    if args.stree:
        call(['stree', repo.work_tree])
        return

    if not command:
        log.error('please provide a git command')
        return 1
    
    makedirs(repo.work_tree)
    repo.git(*command, verbosity=0, indent=False)
