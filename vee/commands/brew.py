from vee.commands.main import command, argument
from vee.exceptions import CliException
from vee.requirement import Requirement


@command(
    help='run a homebrew command',
    parse_known_args=True,
)
def brew(args, *command):

    if not command:
        raise CliException('please specify a homebrew command')

    home = args.assert_home()

    # This is such a hack.
    req = Requirement('homebrew:', home=home)
    req.package._brew(*command)
