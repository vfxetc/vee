from vee.commands.main import command, argument
from vee.requirement import Requirement
from vee.utils import colour


@command(
    argument('--force', action='store_true', help='force install over old package'),
    argument('package', nargs='...'),
    help='install a package',
    usage='vee install [--force] PACKAGE [OPTIONS]',
)
def install(args):

    args.assert_home()
    req = Requirement(args.package, home=args.home)

    def installed_check():
        if req.manager.installed:
            if args.force:
                req.manager.uninstall()
            else:
                print colour('ERROR:', 'red', bright=True), colour(str(req) + ' is already installed', 'black', reset=True)
                return True

    if installed_check():
        return

    req.manager.fetch()
    if installed_check():
        return
    
    req.manager.extract()
    if installed_check():
        return

    req.manager.build()
    req.manager.install()

