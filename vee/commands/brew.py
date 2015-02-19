from vee.commands.main import command, argument
from vee.exceptions import CliException


@command(
    help='run a homebrew command',
    parse_known_args=True,
)
def brew(args, *command):

    if not command:
        raise CliException('please specify a homebrew command')

    args.assert_home()
    manager = args.home.get_package('homebrew', None)
    manager._brew(*command)
