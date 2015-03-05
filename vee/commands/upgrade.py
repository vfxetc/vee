import os

from vee.cli import style
from vee.commands.main import command, argument, group
from vee.utils import makedirs


@command(
    argument('--all', action='store_true', help='upgrade all repositories'),
    argument('--head', action='store_true', help='build head, even if it doesnt match remote branch'),
    argument('--dirty', action='store_true', help='build even when work tree is dirty'),
    argument('repos', nargs='*'),
    help='upgrade packages specified by repositories, and link into environments',
)
def upgrade(args):

    home = args.assert_home()

    if args.all:
        repos = list(home.iter_repos())
    else:
        repos = [home.get_env_repo(x) for x in args.repos] if args.repos else [home.get_env_repo()]

    for repo in repos:

        repo.clone_if_not_exists()

        rev = repo.head if args.head else repo.rev_parse('%s/%s' % (repo.remote_name, repo.branch_name))

        if not args.head and rev != repo.head:
            print style('Error:', 'red', bold=True), style('%s repo not checked out to %s/%s; force with --head' % (
                repo.name, repo.remote_name, repo.branch_name), bold=True)
            continue

        if not args.dirty and list(repo.status()):
            print style('Error:', 'red', bold=True), style('%s repo is dirty; force with --dirty' % repo.name, bold=True)
            continue

        path_by_commit = home._abs_path('environments', repo.name, 'commits', rev[:8])
        path_by_branch = home._abs_path('environments', repo.name, repo.branch_name)

        args.main(['link', path_by_commit, repo.abspath('requirements.txt')])

        # Create a symlink by branch.
        if os.path.exists(path_by_branch):
            os.unlink(path_by_branch)
        makedirs(os.path.dirname(path_by_branch))
        os.symlink(path_by_commit, path_by_branch)


