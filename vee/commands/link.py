from vee.cli import style
from vee.commands.main import command, argument
from vee.environment import Environment
from vee.exceptions import AlreadyInstalled, AlreadyLinked
from vee.requirement import Requirement
from vee.requirementset import RequirementSet


@command(
    argument('--re-install', action='store_true'),
    argument('--no-install', action='store_true'),
    argument('--force', action='store_true'),
    argument('--raw', action='store_true', help='requirements are raw directories'),
    argument('--long-names', action='store_true',
        help='automatically picks package names'),
    argument('environment'),
    argument('requirements', nargs='...'),
    help='link a package, or requirements.txt, into an environment',
    usage='vee link [--raw] ENVIRONMENT REQUIREMENTS',
)
def link(args):

    if args.no_install and args.re_install:
        raise ValueError('please use only one of --no-install and --re-install')

    home = args.assert_home()
    env = Environment(args.environment, home=home)

    if args.raw:
        for dir_ in args.requirements:
            print style('Linking', 'blue', bold=True), style(dir_, bold=True)
            env.link_directory(dir_)
        return

    reqs = RequirementSet(args.requirements, home=home)

    if not args.long_names:
        reqs.guess_names()

    for req in reqs.iter_requirements():

        if args.no_install and not req.installed:
            raise CliError('not installed: %s' % req)

        if not args.re_install:
            req.package.resolve_existing(env=env)

        try:
            req.auto_install(force=args.re_install)
        except AlreadyInstalled:
            pass
        
        try:
            req.package.link(env, force=args.force)
        except AlreadyLinked as e:
            print style('Already linked', 'blue', bold=True), style(str(req), bold=True)
      


