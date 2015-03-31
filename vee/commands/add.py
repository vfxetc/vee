import re

from vee.cli import style, style_error, style_note, style_warning
from vee.commands.main import command, argument
from vee.git import GitRepo, normalize_git_url
from vee.packageset import PackageSet
from vee.requirement import Requirement
from vee.utils import guess_name


@command(
    argument('--update', action='store_true', help='update all repos themselves'),
    argument('--bake-installed', action='store_true', help='bake all installed revisions'),
    argument('--repo'),
    argument('package', nargs='?', default='.'),
    help='record changes to dev packages in environment repo',
)
def add(args):

    home = args.assert_home()
    env_repo = home.get_env_repo(args.repo)
    req_set = env_repo.load_requirements()
    pkg_set = PackageSet(home=home)

    if args.update:
        baked_any = False
        for req in req_set.iter_requirements():
            pkg = pkg_set.resolve(req, check_existing=False)
            if pkg.type != 'git':
                continue
            print style_note('Fetching', str(req))
            pkg.repo.fetch('origin', 'master') # TODO: track these another way?
            if pkg.repo.check_ff_safety('origin/master'):
                pkg.repo.checkout('origin/master')
                head = pkg.repo.head[:8]
                if head != req.revision:
                    req.revision = pkg.repo.head[:8]
                    print style_note('Updated', str(req))
                    baked_any = True
        if baked_any:
            env_repo.dump_requirements(req_set)
        else:
            print style_note('No changes.')
        return

    if args.bake_installed:
        baked_any = False

        for req in req_set.iter_requirements():

            pkg = pkg_set.resolve(req)
            if pkg.type != 'git':
                continue

            if req.name and req.name == guess_name(req.url):
                req.name = None
                baked_any = True
                print style_note('Unset redundant name', req.name)

            if pkg.installed and req.revision != pkg.repo.head[:8]:
                req.revision = pkg.repo.head[:8]
                baked_any = True
                print style_note('Pinned', req.name, req.revision)

        if baked_any:
            env_repo.dump_requirements(req_set)
        else:
            print style_note('No changes.')
        return


    row = home.get_development_record(args.package)

    if not row:
        raise ValueError('No development package %r' % args.package)

    dev_repo = GitRepo(row['path'])

    # Get the normalized origin.
    dev_remote_urls = set()
    for url in dev_repo.remotes().itervalues():
        url = normalize_git_url(url) or url
        dev_remote_urls.add(url)
    if not dev_remote_urls:
        print style_error('No git remotes for %s' % row['path'])
        return 1

    for req in req_set.iter_requirements():
        pkg = pkg_set.resolve(req, check_existing=False)
        if pkg.fetch_type != 'git':
            continue
        
        req_url = normalize_git_url(req.url)
        if req_url in dev_remote_urls:
            if req.revision == dev_repo.head[:8]:
                print style_note('No change to', str(req))
            else:
                req.revision = dev_repo.head[:8]
                print style_note('Updated', str(req))
            break
    else:
        req = Requirement(
            url=normalize_git_url(dev_repo.remotes()['origin'], prefix=True),
            revision=dev_repo.head[:8],
        )
        req_set.append(('', req, ''))

    env_repo.dump_requirements(req_set)
