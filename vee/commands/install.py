from vee.cli import style
from vee.commands.main import command, argument
from vee.exceptions import AlreadyInstalled
from vee.packageset import PackageSet
from vee.requirements import Requirements


@command(
    argument('--force', action='store_true', help='force install over old package'),
    argument('requirements', nargs='...'),
    help='install a package; low-level',
    usage='vee install [--force] PACKAGE [OPTIONS]',
    acquire_lock=True,
)
def install(args):

    home = args.assert_home()

    if not args.requirements:
        raise ValueError('please provide requirements to install')

    reqs = Requirements(args.requirements, home=home)
    pkgs = PackageSet(home=home)

    for req in reqs.iter_packages():
        pkg = pkgs.resolve(req, check_existing=not args.force)
        try:
            pkgs.install(pkg.name, reinstall=args.force)
        except AlreadyInstalled:
            print style('Already installed', 'blue', bold=True), style(str(pkg.freeze()), bold=True)
