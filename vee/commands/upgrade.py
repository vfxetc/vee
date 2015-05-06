from subprocess import CalledProcessError
import os

from vee import log
from vee.cli import style, style_warning
from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.packageset import PackageSet
from vee.utils import makedirs


@command(
    argument('--all', action='store_true', help='upgrade all repositories'),
    argument('--dirty', action='store_true', help='build even when work tree is dirty'),
    argument('--relink', action='store_true', help='relink packages'),
    argument('--reinstall', action='store_true', help='reinstall packages'),
    argument('--no-deps', action='store_true', help='dont touch dependencies'),
    argument('--force-branch-link', action='store_true'),
    argument('-r', '--repo', action='append', dest='repos'),
    argument('subset', nargs='*'),
    help='upgrade packages specified by repositories, and link into environments',
    acquire_lock=True,
)
def upgrade(args):

    home = args.assert_home()

    if args.all:
        repos = list(home.iter_repos())
    else:
        repos = [home.get_env_repo(x) for x in args.repos] if args.repos else [home.get_env_repo()]

    for env_repo in repos:

        env_repo.clone_if_not_exists()

        try:
            head = env_repo.head
        except CalledProcessError:
            print style_warning('no commits in repository')
            head = None

        try:
            remote_head = env_repo.rev_parse('%s/%s' % (env_repo.remote_name, env_repo.branch_name))
        except ValueError:
            print style_warning('tracked %s/%s does not exist in env_repo' % (env_repo.remote_name, env_repo.branch_name))
            remote_head = None

        if remote_head and head != remote_head:
            print style_warning('%s repo not checked out to %s/%s' % (
                env_repo.name, env_repo.remote_name, env_repo.branch_name))

        dirty = bool(list(env_repo.status()))
        if not args.dirty and dirty:
            print style('Error:', 'red', bold=True), style('%s repo is dirty; force with --dirty' % env_repo.name, bold=True)
            continue

        commit_name = (head[:8] + ('-dirty' if dirty else '')) if head else 'nocommit'
        env_name = os.path.join(env_repo.name, 'commits', commit_name)
        env = Environment(env_name, home=home)

        req_set = env_repo.load_requirements()
        pkg_set = PackageSet(env=env, home=home)
        
        # Register the whole set, so that dependencies are pulled from here instead
        # of weakly resolved from installed packages.
        # TODO: This blanket reinstalls things, even if no_deps is set.
        pkg_set.resolve_set(req_set, check_existing=not args.reinstall)

        # Install and/or link.
        pkg_set.install(args.subset or None, link_env=env, reinstall=args.reinstall, relink=args.relink, no_deps=args.no_deps)

        if pkg_set._errored and not args.force_branch_link:
            print style_warning("Not creating branch or version links; force with --force-branch-link")
            continue

        # Create a symlink by branch.
        path_by_branch = home._abs_path('environments', env_repo.name, env_repo.branch_name)
        if os.path.lexists(path_by_branch):
            os.unlink(path_by_branch)
        makedirs(os.path.dirname(path_by_branch))
        os.symlink(env.path, path_by_branch)

        # Create a symlink by version.
        version = req_set.headers.get('Version')
        if version:
            path_by_version = home._abs_path('environments', env_repo.name, 'versions', version.value + ('-dirty' if dirty else ''))
            if os.path.lexists(path_by_version):
                os.unlink(path_by_version)
            makedirs(os.path.dirname(path_by_version))
            os.symlink(env.path, path_by_version)


