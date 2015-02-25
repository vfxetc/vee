from vee.commands.main import command, argument
from vee.requirement import Requirement
from vee.utils import style, guess_name


@command(
    argument('--force', action='store_true', help='force install over old package'),
    argument('--guess-name', action='store_true', help='pick a sensible package name'),
    argument('package', nargs='...'),
    help='install a package',
    usage='vee install [--force] PACKAGE [OPTIONS]',
)
def install(args):

    args.assert_home()

    req = Requirement(args.package, home=args.home)

    if args.guess_name:
        req.name = req.name or guess_name(req.url)
    
    if not args.force:
        req.package.resolve_existing()

    req.install(force=args.force)
    
