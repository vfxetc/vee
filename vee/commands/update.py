from vee.cli import style, style_note, style_warning
from vee.commands.main import command, argument, group
from vee.environment import Environment


@command(
    argument('--all', action='store_true', help='update all repos'),
    argument('--force', action='store_true', help='force checkout, even if not fast-forward'),
    argument('-r', '--repo', action='append', dest='repos'),
    help='update repos',
)
def update(args):

    home = args.assert_home()

    if args.all:
        env_repos = list(home.iter_env_repos())
    else:
        env_repos = [home.get_env_repo(x) for x in args.repos] if args.repos else [home.get_env_repo()]

    retcode = 0

    for env_repo in env_repos:

        print style_note('Updating repo', env_repo.name)

        env_repo.clone_if_not_exists()

        if env_repo.remote_name not in env_repo.remotes():
            print style_warning('"%s" does not have remote "%s"' % (env_repo.name, env_repo.remote_name))
            continue

        rev = env_repo.fetch()

        if not args.force and not env_repo.check_ff_safety(rev):
            print style('Error:', 'red', bold=True), style('Cannot fast-forward; skipping.', bold=True)
            retcode = retcode or 1
            continue

        env_repo.checkout(force=args.force)

    return retcode
