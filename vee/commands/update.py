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
        repos = list(home.iter_repos())
    else:
        repos = [home.get_repo(x) for x in args.repos] if args.repos else [home.get_repo()]

    success = True

    for repo in repos:
        did_update = repo.update(force=args.force)
        success = success and did_update

    return int(not success)
