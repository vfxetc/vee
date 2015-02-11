from vee.commands.main import command, argument, CommandError


@command(
    help='run a homebrew command',
    parse_known_args=True,
)
def brew(args, *command):

    if not command:
        raise CommandError(1, 'please specify a homebrew command')

    args.assert_home()
    manager = args.home.get_manager('homebrew')
    manager._brew(*command)
