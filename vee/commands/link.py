from vee.commands.main import command, argument
from vee.environment import Environment
from vee.requirement import Requirement
from vee.requirementset import RequirementSet
from vee.utils import style
from vee.exceptions import CliException, AlreadyInstalled


@command(
    argument('--raw', action='store_true', help='package is directory, not a requirement'),
    argument('--guess-names', action='store_true'),
    argument('environment'),
    argument('specification', nargs='...'),
    help='link a package',
    usage='vee link [--raw] ENVIRONMENT SPECIFICATION',
)
def link(args):

    args.assert_home()

    env = Environment(args.environment, home=args.home)

    if args.raw:
        for dir_ in args.package:
            print style('Linking', 'blue', bold=True), style(dir_, bold=True)
            env.link_directory(dir_)
        return


    req_set = RequirementSet()
    req_set.parse(args.specification[0], home=args.home)

    if args.guess_names:
        req_set.guess_names()

    for req in req_set.iter_requirements():

        try:
            req.install()
        except AlreadyInstalled:
            pass
        
        print style('Linking', 'blue', bold=True), style(str(req), bold=True)

        req.package.link(env)
        


