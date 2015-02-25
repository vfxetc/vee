from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.utils import style


@command(
    argument('--all', action='store_true', help='update all repos'),
    argument('name', nargs='?'),
    help='update repos',
)
def update(args):

    home = args.assert_home()
    config = home.config

    if args.all:
        repos = list(home.iter_repos())
    else:
        repos = [home.get_repo(args.name)]

    for repo in repos:

        print style('Updating repo "%s"' % repo.name, 'blue', bold=True), style(repo.remote_url, bold=True)

        repo.clone_if_not_exists()

        # This is kinda gross, but we need to do it to make sure that we are
        # fetching from the right URL AND we need to rev-parse a "$remote/master"
        # -ish revision.
        repo.assert_remote_name('origin')
        rev = repo.fetch('origin/master', remote='origin')

        # Check the status of the work tree and index.
        status_ok = True
        for idx, tree, name in repo.status():
            if idx or tree:
                print style('Error:', 'red', bold=True), style('uncomitted changes:', bold=True)
                repo._call('status', silent=True)
                status_ok = False
                break

        # Make sure we haven't forked.
        ahead, behind = repo.distance(repo.head, rev)
        if ahead and behind:
            print style('Error:', 'red', bold=True), style('your and the repo have forked', bold=True)
            status_ok = False
        elif ahead:
            print style('Warning:', 'yellow', bold=True), style('you are %s commits ahead of the remote repo; please `vee push`' % ahead, bold=True)
            status_ok = False
        elif behind:
            print style('You are %d commits behind.' % behind, bold=True)

        # Bail!
        if not status_ok:
            print style('Error:', 'red', bold=True), style('we cannot continue given above conditions', bold=True)
            continue

        repo.checkout(rev)
