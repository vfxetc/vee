from vee.commands.main import command, argument
from vee.requirement import Requirement
from vee.utils import style


@command(
    argument('package', nargs='...'),
    name='install-path',
    help='get install pack of a package',
    usage='vee install-path PACKAGE [OPTIONS]',
)
def install_path(args):
    args.assert_home()
    req = Requirement(args.package, home=args.home)
    if not req.package.installed:
        print >> sys.stderr, 'not installed'
        return 2
    print req.package.install_path
    
