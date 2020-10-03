import argparse

from vee.cli import style
from vee.commands.main import command, argument
from vee.exceptions import AlreadyInstalled
from vee.packageset import PackageSet
from vee.requirements import Requirements


@command(
    argument('--force', action='store_true', help='force install over old package'),
    argument('requirements', nargs='...', help=argparse.SUPPRESS),
    help='install a package; low-level',
    usage='vee install [--force] {PACKAGE [OPTIONS], REQUIREMENTS_FILE}+',
    acquire_lock=True,
    group='plumbing',
)
def install(args):
    """Install the given requirements without linking them into an environment.
    This is a low-level command, and is generally unused.

    Examples:

        # Install a single package.
        vee install git+git@github.com:vfxetc/sgmock

        # Install multiple packages.
        vee install git+git@github.com:vfxetc/sgmock git+git@github.com:vfxetc/sgsession \\
            http:/example.org/path/to/tarball.tgz --make-install

        # Install from a requirement set.
        vee install path/to/requirements.txt

    """

    home = args.assert_home()

    if not args.requirements:
        raise ValueError('please provide requirements to install')

    reqs = Requirements(args.requirements, home=home)
    pkgs = PackageSet(home=home)

    # TODO: Resolve everything at once like upgrade does.
    for req in reqs.iter_packages():
        pkg = pkgs.resolve(req, check_existing=not args.force)
        try:
            pkgs.install(pkg.name, reinstall=args.force)
        except AlreadyInstalled:
            log.info(style_note('Already installed', str(pkg.freeze())))
