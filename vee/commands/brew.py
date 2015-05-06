from vee.commands.main import command, argument
from vee.package import Package
from vee.packageset import PackageSet
from vee.homebrew import Homebrew

@command(
    help='run a homebrew command',
    parse_known_args=True,
    acquire_lock=True,
)
def brew(args, *command):

    if not command:
        raise ValueError('please specify a homebrew command')

    home = args.assert_home()
    brew = Homebrew(home=home)
    brew(*command, verbosity=0, indent=False)
