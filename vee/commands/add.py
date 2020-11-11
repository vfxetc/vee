import os
import re

from vee.cli import style, style_error, style_note, style_warning
from vee.commands.main import command, argument
from vee.git import GitRepo, normalize_git_url, get_default_branch
from vee.packageset import PackageSet
from vee.package import Package
from vee.utils import guess_name, checksum_file
from vee import log


@command(
    argument('--update', action='store_true', help='update all repos themselves'),
    argument('--bake-installed', action='store_true', help='bake all installed revisions'),
    argument('--checksum', action='store_true', help='checksum existing packages'),
    argument('--init', action='store_true', help='create if not found in requirements'),
    argument('--repo'),
    argument('package', nargs='?', default='.'),
    help='record changes to dev packages in environment repo',
    group='development',
)
def add(args):

    home = args.assert_home()
    env_repo = home.get_env_repo(args.repo)
    req_set = env_repo.load_manifest()
    pkg_set = PackageSet(home=home)

    baked_any = None

    if args.update:
        baked_any = False
        for req in req_set.iter_packages():
            pkg = pkg_set.resolve(req, check_existing=False)
            if pkg.fetch_type != 'git':
                continue
            log.info(style_note('Fetching', str(req)))
            branch = get_default_branch()
            pkg.repo.fetch('origin', branch) # TODO: track these another way?
            if pkg.repo.check_ff_safety('origin/' + branch):
                pkg.repo.checkout('origin/' + branch)
                head = pkg.repo.head[:8]
                if head != req.revision:
                    req.revision = pkg.repo.head[:8]
                    log.info(style_note('Updated', str(req)))
                    baked_any = True

    if args.bake_installed:
        baked_any = False

        for req in req_set.iter_packages():

            pkg = pkg_set.resolve(req)
            if pkg.fetch_type != 'git':
                continue
            repo = pkg.pipeline.steps['fetch'].repo
            
            if req.name and req.name == guess_name(req.url):
                req.name = None
                baked_any = True
                log.info(style_note('Unset redundant name', req.name))

            if pkg.installed and req.revision != repo.head[:8]:
                req.revision = repo.head[:8]
                baked_any = True
                log.info(style_note('Pinned', req.name, req.revision))

    if args.checksum:
        baked_any = False

        for req in req_set.iter_packages():
            pkg = pkg_set.resolve(req)
            if pkg.checksum:
                continue
            if not pkg.package_path or not os.path.isfile(pkg.package_path):
                continue
            req.checksum = checksum_file(pkg.package_path)
            log.info(style_note('Checksummed', pkg.name, req.checksum))
            baked_any = True

    if baked_any is not None:
        if baked_any:
            env_repo.dump_manifest(req_set)
        else:
            log.info(style_note('No changes.'))
        return

    dev_repo = home.find_development_package(args.package)
    if not dev_repo:
        raise ValueError('No development package %r' % args.package)

    # Get the normalized origin.
    dev_remote_urls = set()
    for url in dev_repo.remotes().values():
        url = normalize_git_url(url, prefer='scp') or url
        log.debug('adding dev remote url: %s' % url)
        dev_remote_urls.add(url)
    if not dev_remote_urls:
        log.info(style_error('No git remotes for %s' % row['path']))
        return 1

    for req in req_set.iter_packages(eval_control=False):

        # We only deal with git packages.
        pkg = pkg_set.resolve(req, check_existing=False)
        if pkg.fetch_type != 'git':
            continue
        
        req_url = normalize_git_url(req.url, prefer='scp')
        log.debug('does match package url?: %s' % req_url)
        if req_url in dev_remote_urls:
            if req.revision == dev_repo.head[:8]:
                log.info(style_note('No change to', str(req)))
            else:
                req.revision = dev_repo.head[:8]
                log.info(style_note('Updated', str(req)))
            break

    else:
        if not args.init:
            log.error('{error}: No required package {name}; would match one of:'.format(error=style('Error', 'red'), name=style(args.package, bold=True)))
            for url in sorted(dev_remote_urls):
                log.info('    {}'.format(url))
            log.info('Use {} to setup: git+{} --revision {}'.format(
                style('vee add --init %s' % args.package, 'green'),
                dev_repo.remotes()['origin'],
                dev_repo.head[:8]
            ))
            return 1

        req = Package(
            url=normalize_git_url(dev_repo.remotes()['origin'], prefix=True),
            revision=dev_repo.head[:8],
            home=home,
        )
        req_set.append(('', req, ''))

    env_repo.dump_manifest(req_set)
