from vee.commands.main import command, argument, group


@command(
    argument('--all', action='store_true', help='upgrade all repositories'),
    argument('-u', '--update', action='store_true', help='update before upgrading'),
    argument('--dirty', action='store_true', help='build even when work tree is dirty'),
    argument('--relink', action='store_true', help='relink packages'),
    argument('--reinstall', action='store_true', help='reinstall packages'),
    argument('--no-deps', action='store_true', help='dont touch dependencies'),
    argument('-f', '--force-branch-link', action='store_true'),
    argument('-r', '--repo', action='append', dest='repos'),
    argument('subset', nargs='*'),
    help='upgrade packages specified by repositories, and link into environments',
    acquire_lock=True,
    group='workflow'
)
def upgrade(args):
    """Install packages and link into environments, as specified by repositories.
    """
    
    home = args.assert_home()

    if args.all:
        repos = list(home.iter_repos())
    else:
        repos = [home.get_repo(x) for x in args.repos] if args.repos else [home.get_repo()]

    success = True

    for repo in repos:

        if args.update:
            # We don't pass through force here. If you need to force it;
            # run via the `update` command.
            if not repo.update():
                success = False
                continue

        success = repo.upgrade(
            dirty=args.dirty,
            force_branch_link=args.force_branch_link,
            no_deps=args.no_deps,
            reinstall=args.reinstall,
            relink=args.relink,
            subset=args.subset,
        ) and success

    return int(not success)
    