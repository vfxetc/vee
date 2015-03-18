import os

from vee.cli import style
from vee.commands.main import command, argument
from vee.environment import Environment
from vee.exceptions import AlreadyInstalled, AlreadyLinked
from vee.requirement import Requirement
from vee.requirementset import RequirementSet
from vee import log


@command(
    argument('--reinstall', action='store_true'),
    argument('--no-install', action='store_true'),
    argument('--force', action='store_true'),

    argument('--raw', action='store_true', help='arguments are raw directories'),

    argument('-r', '--repo'),
    argument('-e', '--environment'),
    argument('-d', '--directory'),

    argument('requirements', nargs='...'),
    help='link a package, or requirements.txt, into an environment',
    usage='vee link [--raw] ENVIRONMENT REQUIREMENTS',
)
def link(args):

    if args.no_install and args.re_install:
        raise ValueError('please use only one of --no-install and --re-install')

    home = args.assert_home()

    if sum(int(bool(x)) for x in (args.repo, args.environment, args.directory)) > 1:
        raise ValueError('use only one of --repo, --environment, or --directory')

    if args.environment:
        env = Environment(args.environment, home=home)
    elif args.directory:
        env = Environment(os.path.abspath(args.directory), home=home)
    else:
        env_repo = home.get_env_repo(args.repo)
        env = Environment('%s/%s' % (env_repo.name, env_repo.branch_name), home=home)


    if args.raw:
        for dir_ in args.requirements:
            print style('Linking', 'blue', bold=True), style(dir_, bold=True)
            env.link_directory(dir_)
        return

    reqs = RequirementSet(args.requirements, home=home)
    reqs.guess_names()

    for req in reqs.iter_requirements():

        log.info(style('==> %s' % req.name, 'blue'))

        if args.no_install and not req.installed:
            raise CliError('not installed: %s' % req)

        if not args.reinstall:
            req.package.resolve_existing(env=env)

        try:
            with log.indent():
                req.auto_install(force=args.reinstall)
        except AlreadyInstalled:
            pass
        
        try:
            req.package.link(env, force=args.force)
        except AlreadyLinked as e:
            log.info(style('Already linked ', 'blue') + str(req), verbosity=1)
      


