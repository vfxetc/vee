import os
from subprocess import CalledProcessError

from vee.cli import style, style_warning
from vee.commands.main import command, argument, group
from vee.utils import makedirs


@command(
    argument('--all', action='store_true', help='upgrade all repositories'),
    argument('--dirty', action='store_true', help='build even when work tree is dirty'),
    argument('--relink', action='store_true', help='relink packages'),
    argument('--reinstall', action='store_true', help='reinstall packages'),
    argument('-r', '--repo', action='append', dest='repos'),
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

        try:
            head = repo.head
        except CalledProcessError:
            print style_warning('no commits in repository')
            head = None

        try:
            remote_head = repo.rev_parse('%s/%s' % (repo.remote_name, repo.branch_name))
        except ValueError:
            print style_warning('tracked %s/%s does not exist in repo' % (repo.remote_name, repo.branch_name))
            remote_head = None

        if remote_head and head != remote_head:
            print style_warning('%s repo not checked out to %s/%s' % (
                repo.name, repo.remote_name, repo.branch_name))

        dirty = bool(list(repo.status()))
        if not args.dirty and dirty:
            print style('Error:', 'red', bold=True), style('%s repo is dirty; force with --dirty' % repo.name, bold=True)
            continue

        path_by_commit = home._abs_path('environments', repo.name, 'commits', (head[:8] + ('-dirty' if dirty else '')) if head else 'nocommit')
        path_by_branch = home._abs_path('environments', repo.name, repo.branch_name)

        cmd = ['link']
        if args.relink:
            cmd.append('--force')
        if args.reinstall:
            cmd.append('--reinstall')
        cmd.extend((path_by_commit, repo.abspath('requirements.txt')))
        args.main(cmd)

        # Create a symlink by branch.
        if os.path.lexists(path_by_branch):
            os.unlink(path_by_branch)
        makedirs(os.path.dirname(path_by_branch))
        os.symlink(path_by_commit, path_by_branch)


