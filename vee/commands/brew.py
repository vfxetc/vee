from vee.commands.main import command, argument, CommandError
from vee.requirements import Requirement


@command(
    help='run a homebrew command',
    parse_known_args=True,
)
def brew(args, *command):

    if not command:
        raise CommandError(1, 'please specify a homebrew command')

    req = Requirement.parse('homebrew+NotARealPackage')

    args.assert_home()
    manager, package = args.home.load_requirement(req)

    manager._brew(*command)


