from vee.commands.main import command, argument
from vee.package import Package


@command(
    argument('package', nargs='...'),
    help='install a package',
    usage='vee install PACKAGE [OPTIONS]',
)
def install(args):
    args.assert_home()
    package = Package.parse(args.package, home=args.home)
    package.fetch()
    package.install()

