import argparse
import os

from vee import log
from vee.cli import style
from vee.commands.main import command, argument
from vee.environment import Environment
from vee.exceptions import AlreadyInstalled, AlreadyLinked, print_cli_exc
from vee.package import Package
from vee.packageset import PackageSet
from vee.requirements import Requirements


@command(
    argument('--reinstall', action='store_true'),
    argument('--no-install', action='store_true'),
    argument('--force', action='store_true'),

    argument('--raw', action='store_true', help='arguments are raw directories'),

    argument('-r', '--repo'),
    argument('-e', '--environment'),
    argument('-d', '--directory'),

    argument('--subset', action='append', help=argparse.SUPPRESS),

    argument('requirements', nargs='...'),
    help='link a package, or requirements.txt, into an environment',
    acquire_lock=True,
    group='plumbing',
    usage='vee link ENVIRON (REQUIREMENT [OPTIONS])+',
)
def link(args):
    """Link the given requirement or requirements into the given environment,
    e.g.::
        
        # Install and link a single package.
        $ vee link git+git@github.com:vfxetc/sgmock

        # Install and link multiple packages.
        $ vee link git+git@github.com:vfxetc/sgmock git+git@github.com:vfxetc/sgsession \\
            http:/example.org/path/to/tarball.tgz --make-install

        # Install and link from a requirement set.
        $ vee link path/to/requirements.txt

    """

    if args.no_install and args.re_install:
        raise ValueError('please use only one of --no-install and --re-install')

    home = args.assert_home()

    if sum(int(bool(x)) for x in (args.repo, args.environment, args.directory)) > 1:
        raise ValueError('use only one of --repo, --environment, or --directory')

    if args.environment:
        env = Environment(args.environment, home=home)
    elif args.directory:
        env = Environment(os.path.abspath(args.directory), home=home)
    else:
        env_repo = home.get_env_repo(args.repo)
        env = Environment('%s/%s' % (env_repo.name, env_repo.branch_name), home=home)


    if args.raw:
        for dir_ in args.requirements:
            print style('Linking', 'blue', bold=True), style(dir_, bold=True)
            env.link_directory(dir_)
        return

    req_set = Requirements(args.requirements, home=home)
    pkg_set = PackageSet(env=env, home=home)
    
    # Register the whole set, so that dependencies are pulled from here instead
    # of weakly resolved from installed packages.
    pkg_set.resolve_set(req_set)

    for req in req_set.iter_packages():

        # Skip if it wasn't requested.
        if args.subset and req.name not in args.subset:
            continue

        log.info(style('==> %s' % req.name, 'blue'))

        pkg = pkg_set.resolve(req, check_existing=not args.reinstall)

        if args.no_install and not pkg.installed:
            raise CliError('not installed: %s' % req)

        try:
            with log.indent():
                pkg_set.install(pkg.name, link_env=env, reinstall=args.reinstall, relink=args.force)
        except AlreadyInstalled:
            pass
        except AlreadyLinked as e:
            log.info(style('Already linked ', 'blue') + str(req), verbosity=1)
        except Exception as e:
            print_cli_exc(e, verbose=True)
            log.exception('Failed to link %s' % req)
            continue
        

