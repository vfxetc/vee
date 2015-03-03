from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.utils import style


@command(
    argument('--all', action='store_true', help='update all repos'),
    argument('--force', action='store_true', help='force checkout, even if not fast-forward'),
    argument('repos', nargs='*'),
    help='update repos',
)
def update(args):

    home = args.assert_home()

    if args.all:
        repos = list(home.iter_repos())
    else:
        repos = [home.get_repo(x) for x in args.repos] if args.repos else [home.get_repo()]

    retcode = 0

    for repo in repos:

        print style('Updating repo "%s"' % repo.name, 'blue', bold=True), style(repo.remote_url, bold=True)

        repo.clone_if_not_exists()

        # This is kinda gross, but we need to do it to make sure that we are
        # fetching from the right URL AND we need to rev-parse a "$remote/master"
        # -ish revision.
        remote = repo.assert_remote_name()
        rev = repo.fetch('%s/master' % remote, remote=remote)

        if not args.force and not repo.check_ff_safety(rev):
            print style('Error:', 'red', bold=True), style('Cannot fast-forward; skipping.', bold=True)
            retcode = retcode or 1
            continue

        repo.checkout(rev)

    return retcode
