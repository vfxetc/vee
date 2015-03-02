from vee.commands.main import command, argument
from vee.environment import Environment
from vee.requirement import Requirement
from vee.requirementset import RequirementSet
from vee.utils import style
from vee.exceptions import CliException, AlreadyInstalled, AlreadyLinked


@command(
    argument('--reinstall', action='store_true'),
    argument('--force', action='store_true'),
    argument('--raw', action='store_true', help='package is directory, not a requirement'),
    argument('--long-names', action='store_true',
        help='automatically picks package names'),
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

    unknown_args = args.specification
    while unknown_args:
        req_args, unknown_args = Requirement._arg_parser.parse_known_args(unknown_args)
        if req_args.url.endswith('.txt'):
            req_set.parse(req_args.url, home=args.home)
        else:
            req_set.elements.append(('', Requirement(req_args, home=args.home), ''))

    if not args.long_names:
        req_set.guess_names()

    for req in req_set.iter_requirements():

        if not args.reinstall:
            req.package.resolve_existing(env=env)

        try:
            req.install(force=args.reinstall)
        except AlreadyInstalled:
            pass
        
        try:
            req.package.link(env, force=args.force)
        except AlreadyLinked as e:
            print style('Already linked', 'blue', bold=True), style(str(req), bold=True),
            print style('(link %s)' % e.args[1], faint=True)
        


