import re
import os
import subprocess
import tempfile

from vee.cli import style, style_error, style_note
from vee.commands.main import command, argument
from vee.git import GitRepo, normalize_git_url
from vee.packageset import PackageSet


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

    if args.semver_level is None:
        args.semver_level = 0 if args.micro else 2

    if args.message is None:

        dev_pkgs = {pkg.name: pkg for pkg in home.iter_development_packages()}
        pkg_set = PackageSet(home=home)
        by_name = {}
        for revision, name in [
            (None, 'work'),
            ('HEAD', 'head'),
        ]:
            for req in env_repo.load_requirements(revision=revision).iter_packages():
                pkg = pkg_set.resolve(req, check_existing=False)
                if pkg.fetch_type != 'git':
                    continue
                by_name.setdefault(pkg.name, {})[name] = req

        commits = []
        for pkg_name, reqs in sorted(by_name.items()):
            new = reqs['work']
            old = reqs['head']
            if new.revision == old.revision:
                continue
            dev = dev_pkgs.get(pkg_name)
            for line in dev.git('log', '--pretty=%cI %h %s', '{}...{}'.format(old.revision, new.revision), stdout=True).splitlines():
                line = line.strip()
                if not line:
                    continue
                time, hash_, subject = line.split(' ', 2)
                commits.append((time, pkg_name, '[{} {}] {}'.format(pkg_name, hash_, subject)))

        if commits:

            if len(commits) == 1:
                default_message = [commits[0][2]]
            else:
                pkg_names = set(c[1] for c in commits)
                default_message = ['{} commit{} in {} package{}: {}.'.format(
                    len(commits), 's' if len(commits) != 1 else '',
                    len(pkg_names), 's' if len(pkg_names) != 1 else '',
                    ', '.join(sorted(pkg_names)),
                ), '']
                for c in commits:
                    default_message.append(c[2])

        else:

            default_message = [default_messages[args.semver_level]]

        fd, path = tempfile.mkstemp('.txt', 'vee-commit-msg.')
        with open(path, 'w') as fh:
            fh.write('\n'.join(default_message))
            fh.write('''

# Please enter the commit message for your changes. Lines starting
# with '#' will be ignored, and an empty message aborts the commit.
''')

        editor = os.environ.get('EDITOR', 'vim')
        editor_args = [editor, path]
        if editor == 'vim':
            editor_args.insert(1, r'+syntax match Comment "^\s*#.*$"')
        code = subprocess.call(editor_args)

        message = open(path).readlines()
        os.close(fd)
        os.unlink(path)

        if code:
            print style_error("Editor ({}) failed".format(editor), "and returned code {}".format(code))
            return

        message = [line.rstrip() for line in message if not line.lstrip().startswith('#')]
        message = '\n'.join(message).strip()
        if not message:
            return

        args.message = message

    env_repo.commit(args.message, args.semver_level)
