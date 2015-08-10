from vee.commands.main import command, argument
from vee.package import Package
from vee.packageset import PackageSet
from vee.homebrew import Homebrew

@command(
    help='run a homebrew command',
    parse_known_args=True,
    acquire_lock=True,
    group='plumbing',
    usage='vee brew COMMAND+'
)
def brew(args, *command):
    """Run a command on VEE's Homebrew. This is sometimes nessesary to manage Homebrew
    dependencies, as they are generally outside of the standard build pipeline.

    E.g.::
        
        $ vee brew install sqlite
        ==> Installing sqlite dependency: readline
        ==> Installing sqlite

        $ vee brew list
        readline sqlite

    """

    if not command:
        raise ValueError('please specify a homebrew command')

    home = args.assert_home()
    brew = Homebrew(home=home)
    brew(*command, verbosity=0, indent=False)
