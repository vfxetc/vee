from vee.cli import style, style_note, style_warning
from vee.commands.main import command, argument, group
from vee.environment import Environment


@command(
    argument('--all', action='store_true', help='update all repos'),
    argument('--force', action='store_true', help='force checkout, even if not fast-forward'),
    argument('-r', '--repo', action='append', dest='repos'),
    help='update repos',
    acquire_lock=True,
    group='workflow',
)
def update(args):
    """Update the environment repository (via `git pull`). This will fail if
    your repositories are dirty, or have forked from their remotes.
    """

    home = args.assert_home()

    if args.all:
        env_repos = list(home.iter_env_repos())
    else:
        env_repos = [home.get_env_repo(x) for x in args.repos] if args.repos else [home.get_env_repo()]

    success = True

    for env_repo in env_repos:
        did_update = env_repo.update(force=args.force)
        success = success and did_update

    return int(not success)
