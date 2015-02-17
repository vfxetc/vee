from vee.commands.main import command, argument
from vee.requirement import Requirement
from vee.utils import colour


@command(
    argument('package', nargs='...'),
    name='install-path',
    help='get install pack of a package',
    usage='vee install-path PACKAGE [OPTIONS]',
)
def install_path(args):
    args.assert_home()
    req = Requirement(args.package, home=args.home)
    if not req.manager.installed:
        print >> sys.stderr, 'not installed'
        return 2
    print req.manager.install_path
    
