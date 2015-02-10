from vee.commands.main import command, argument
from vee.requirements import Requirement

@command(
    help='install a package',
    parents=[Requirement.arg_parser],
)
def install(args):

    req = Requirement.parse(args)
    print req

    args.assert_home()
    
    manager, package = args.home.load_requirement(req)

    print manager
    print package

