import os

from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.utils import style, makedirs


@command(
    argument('--all', action='store_true', help='update all repos'),
    argument('name', nargs='?'),
    help='update repos',
)
def upgrade(args):

    home = args.assert_home()
    config = home.config

    if args.all:
        repos = list(home.iter_repos())
    else:
        repos = [home.get_repo(args.name)]

    for repo in repos:

        # TODO: the same status checks as update.

        rev = repo.rev_parse('%s/%s' % (repo.remote_name, repo.branch_name))

        if rev != repo.head:
            print style('Error:', 'red', bold=True), style('%s repo not checked out to %s/%s' % (
                repo.name, repo.remote_name, repo.branch_name), bold=True)
            continue

        if list(repo.status()):
            print style('Error:', 'red', bold=True), style('%s repo is dirty' % repo.name, bold=True)
            continue

        path_by_commit = home.abspath('environments', repo.name, 'commits', rev[:8])
        path_by_branch = home.abspath('environments', repo.name, repo.remote_name, repo.branch_name)

        args.main(['link', path_by_commit, repo.abspath('requirements.txt')])

        if os.path.exists(path_by_branch):
            os.unlink(path_by_branch)

        makedirs(os.path.dirname(path_by_branch))
        os.symlink(path_by_commit, path_by_branch)


