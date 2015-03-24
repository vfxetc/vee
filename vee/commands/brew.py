from vee.commands.main import command, argument
from vee.requirement import Requirement
from vee.packageset import PackageSet


@command(
    help='run a homebrew command',
    parse_known_args=True,
)
def brew(args, *command):

    if not command:
        raise ValueError('please specify a homebrew command')

    home = args.assert_home()

    # This is such a hack.
    req = Requirement('homebrew:', home=home)
    pkg = PackageSet(home=home).resolve(req)
    pkg._brew(*command, verbosity=0, indent=False)
