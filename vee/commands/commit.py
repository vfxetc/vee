import re

from vee.cli import style, style_error, style_note
from vee.commands.main import command, argument
from vee.git import GitRepo, normalize_git_url


default_messages = {
    0: 'major changes  (e.g. backwards incompatible)',
    1: 'minor changes (e.g. extended features)',
    2: 'patch-level changes (e.g. bug fixes)',
    None: 'micro changes (e.g. config or build)',
}

@command(
    argument('--major', action='store_const', dest='semver_level', const=0),
    argument('--minor', action='store_const', dest='semver_level', const=1),
    argument('--patch', action='store_const', dest='semver_level', const=2),
    argument('--micro', action='store_true'),
    argument('-r', '--repo'),
    argument('-m', '--message'),
    help='commit changes to environment repo',
    group='development',
)
def commit(args):

    home = args.assert_home()
    env_repo = home.get_env_repo(args.repo)

    if not env_repo.status():
        print style_error('Nothing to commit.')
        return 1

    # Pick the level of the patch.
    while not args.micro and args.semver_level is None:
        print '%s [%s]:' % (
            style('How severe are the changes?', 'green', bold=True),
            style('major,minor,PATCH,micro', faint=True),
        ),
        res = raw_input().strip() or 'patch'
        try:
            args.semver_level = dict(major=0, minor=1, patch=2, micro=None)[res]
        except KeyError:
            pass
        else:
            break

    if args.message is None:
        default_message = default_messages[args.semver_level]
        print '%s [%s]:' % (
            style('Enter a short commit message', 'green', bold=True),
            style(default_message, faint=True),
        ),
        args.message = raw_input().strip() or default_message

    env_repo.commit(args.message, args.semver_level)
