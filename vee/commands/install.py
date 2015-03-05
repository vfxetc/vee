from vee.cli import style
from vee.commands.main import command, argument
from vee.exceptions import AlreadyInstalled
from vee.requirementset import RequirementSet


@command(
    argument('--force', action='store_true', help='force install over old package'),
    argument('--long-names', action='store_true', help='don\'t automatically pick names'),
    argument('requirements', nargs='...'),
    help='install a package',
    usage='vee install [--force] PACKAGE [OPTIONS]',
)
def install(args):

    home = args.assert_home()

    reqs = RequirementSet(args.requirements, home=home)

    if not args.long_names:
        reqs.guess_names()

    for req in reqs.iter_requirements():
        if not args.force:
            req.package.resolve_existing()
        try:
            req.auto_install(force=args.force)
        except AlreadyInstalled:
            print style('Already installed', 'blue', bold=True), style(str(req.package.freeze()), bold=True)
    
