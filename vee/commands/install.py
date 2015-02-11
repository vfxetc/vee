from vee.commands.main import command, argument
from vee.package import Package


@command(
    help='install a package',
    parents=[Package.arg_parser],
)
def install(args):
    args.assert_home()
    package = Package.parse(args)
    package.fetch()
    package.install()

