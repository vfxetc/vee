from vee.cli import style
from vee.commands.main import command, argument
from vee.exceptions import AlreadyInstalled
from vee.packageset import PackageSet
from vee.requirementset import RequirementSet


@command(
    argument('--force', action='store_true', help='force install over old package'),
    argument('requirements', nargs='...'),
    help='install a package; low-level',
    usage='vee install [--force] PACKAGE [OPTIONS]',
)
def install(args):

    home = args.assert_home()

    if not args.requirements:
        raise ValueError('please provide requirements to install')

    req_set = RequirementSet(args.requirements, home=home)
    pkg_set = PackageSet(home=home)

    for req in req_set.iter_requirements():
        pkg = pkg_set.resolve(req, check_existing=not args.force)
        try:
            pkg_set.auto_install(pkg.name, force=args.force)
        except AlreadyInstalled:
            print style('Already installed', 'blue', bold=True), style(str(pkg.freeze()), bold=True)
    
