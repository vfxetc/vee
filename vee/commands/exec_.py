import os

from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.exceptions import CliException
from vee.requirementset import RequirementSet
from vee.utils import guess_environ


@command(
    argument('--export', action='store_true'),
    argument('-r', '--requirements'),
    argument('-e', '--environment'),
    argument('command', nargs='...'),
    name='exec',
    help='execute in this environment',
    usage='vee exec (-r REQUIREMENTS | ENVIRONMENT) COMMAND [...]',
)
def exec_(args):

    if not (args.requirements or args.environment):
        raise CliException('Must provide either requirements or environment')
    if not (args.export or args.command):
        raise CliException('Must either --export or provide a command')

    args.assert_home()
    
    paths = []

    if args.requirements:
        req_set = RequirementSet()
        req_set.parse(args.requirements, home=args.home)
        for req in req_set.iter_requirements():
            req.package.resolve_existing()
            req.package._assert_paths(install=True)
            if not req.package.installed:
                raise CliException('Requirement is not installed: %s' % req)
            paths.append(req.package.install_path)

    if args.environment:
        env = Environment(args.environment, home=args.home)
        paths.append(env.path)

    environ_diff = guess_environ(paths)

    if args.export:
        for k, v in sorted(environ_diff.iteritems()):
            print 'export %s="%s"' % (k, v)
        return

    environ = os.environ.copy()
    environ.update(environ_diff)
    os.execvpe(args.command[0], args.command, environ)
