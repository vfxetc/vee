import re

from vee.cli import style, style_error, style_note
from vee.commands.main import command, argument
from vee.exceptions import CliException
from vee.git import GitRepo, normalize_git_url


@command(
    argument('--update', action='store_true', help='update all repos themselves'),
    argument('--bake-installed', action='store_true', help='bake all installed revisions'),
    argument('package', nargs='?', default='.'),
)
def add(args):

    home = args.assert_home()

    if args.update:
        env_repo = home.get_env_repo()
        baked_any = False
        for req in env_repo.iter_git_requirements(home):
            pkg = req.package
            print style_note('Fetching', str(req))
            pkg.repo.fetch('origin/master', remote='origin')
            if pkg.repo.check_ff_safety('origin/master'):
                pkg.repo.checkout('origin/master')
                head = pkg.repo.head[:8]
                if head != req.revision:
                    req.revision = pkg.repo.head[:8]
                    print style_note('Updated', str(req))
                    baked_any = True
        if baked_any:
            env_repo.dump()
        else:
            print style_note('No changes.')
        return

    if args.bake_installed:
        env_repo = home.get_env_repo()
        baked_any = False
        for req in env_repo.iter_git_requirements(home):
            pkg = req.package
            pkg.resolve_existing()
            if pkg.installed and req.revision != pkg.repo.head[:8]:
                req.revision = pkg.repo.head[:8]
                print style_note('Baked', str(req))
                baked_any = True
            else:
                print pkg.installed, pkg.repo.head[:8]
        if baked_any:
            env_repo.dump()
        else:
            print style_note('No changes.')
        return


    row = home.get_development_record(args.package)

    if not row:
        raise CliException('No development package %r' % args.package)

    pkg_repo = GitRepo(row['path'])

    # Get the normalized origin.
    pkg_url = pkg_repo.remotes().get('origin')
    if not pkg_url:
        raise CliException('%s does not have an origin' % row['path'])
    pkg_url = normalize_git_url(pkg_url)
    if not pkg_url:
        raise CliException('%s does not appear to be a git url' % pkg_url)

    env_repo = home.get_env_repo()
    for req in env_repo.iter_git_requirements(home):
        req_url = normalize_git_url(req.url)
        if req_url == pkg_url:
            break
    else:
        raise CliException('could not find matching package')

    if req.revision == pkg_repo.head[:8]:
        print style_note('No change to', str(req))
    else:
        req.revision = pkg_repo.head[:8]
        print style_note('Updated', str(req))
        env_repo.dump()
