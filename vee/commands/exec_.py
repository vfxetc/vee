import os

from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.exceptions import CliException
from vee.requirementset import RequirementSet
from vee.utils import guess_environ


@command(
    argument('--export', action='store_true'),
    argument('-r', '--requirements'),
    argument('--repo'),
    argument('-e', '--environment'),
    argument('command', nargs='...'),
    name='exec',
    help='execute in this environment',
    usage='vee exec (-r REQUIREMENTS | ENVIRONMENT) COMMAND [...]',
)
def exec_(args):

    home = args.assert_home()


    if not (args.export or args.command):
        raise CliException('Must either --export or provide a command')

    if not (args.requirements or args.environment):
        repo = home.get_repo(args.repo)
        args.environment = '%s/%s/%s' % (repo.name, repo.remote_name, repo.branch_name)
    
    paths = []

    if args.requirements:
        req_set = RequirementSet()
        req_set.parse(args.requirements, home=home)
        for req in req_set.iter_requirements():
            req.package.resolve_existing()
            req.package._assert_paths(install=True)
            if not req.package.installed:
                raise CliException('Requirement is not installed: %s' % req)
            paths.append(req.package.install_path)

    if args.environment:
        env = Environment(args.environment, home=home)
        paths.append(env.path)

    environ_diff = guess_environ(paths)

    if args.export:
        for k, v in sorted(environ_diff.iteritems()):
            print 'export %s="%s"' % (k, v)
        return

    environ = os.environ.copy()
    environ.update(environ_diff)
    os.execvpe(args.command[0], args.command, environ)
