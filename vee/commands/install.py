from vee.commands.main import command, argument
from vee.requirement import Requirement


@command(
    argument('package', nargs='...'),
    help='install a package',
    usage='vee install PACKAGE [OPTIONS]',
)
def install(args):
    args.assert_home()
    req = Requirement(args.package, home=args.home)
    if req.manager.installed:
        print req, 'is already installed'
    else:
        req.install()

