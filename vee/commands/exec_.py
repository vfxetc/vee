import os
import re

from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.exceptions import CliException
from vee.requirementset import RequirementSet
from vee.utils import guess_environ


@command(
    argument('--export', action='store_true', help='export the environment instead of executing in it'),
    argument('-R', '--requirements', action='append', help='requirements or requirements files to include; may be comma separated'),
    argument('-r', '--repo', action='append', help='a repo whose HEAD to include; defaults to the default repo'),
    argument('-e', '--environment', action='append', help='an environment to include'),
    argument('command', nargs='...', help='the command to run'),
    name='exec',
    help='execute in this environment',
    usage='vee exec (-r REQUIREMENTS | ENVIRONMENT) COMMAND [...]',
)
def exec_(args):

    home = args.assert_home()

    if not (args.export or args.command):
        raise CliException('Must either --export or provide a command')

    # Default to the default repo.
    if not (args.requirements or args.environment or args.repo):
        args.repo = [None]
    
    paths = []

    # Named (or default) repos.
    for name in args.repo or ():
        repo = home.get_repo(name or None) # Allow '' to be the default.
        args.environment = args.environment or []
        args.environment.append('%s/%s/%s' % (repo.name, repo.remote_name, repo.branch_name))

    # Requirements and requirement sets.
    req_args = []
    for arg in args.requirements or ():
        req_args.extend(arg.split(','))
    reqs = RequirementSet(home=home)
    reqs.parse_args(req_args)
    for req in reqs.iter_requirements():
        req.package.resolve_existing()
        req.package._assert_paths(install=True)
        if not req.package.installed:
            raise CliException('Requirement is not installed: %s' % req)
        paths.append(req.package.install_path)

    # Named environments.
    for name in args.environment or ():
        env = Environment(name, home=home)
        paths.append(env.path)

    environ_diff = guess_environ(paths)

    # More environment variables.
    command = args.command or []
    while command and re.match(r'^\w+=', command[0]):
        k, v = command.pop(0).split('=', 1)
        environ_diff[k] = v

    # Print it out instead of running it.
    if args.export:
        for k, v in sorted(environ_diff.iteritems()):
            existing = os.environ.get(k)
            if existing is not None:
                v = v.replace(existing, '$' + k)
            print 'export %s="%s"' % (k, v)
        return

    environ = os.environ.copy()
    environ.update(environ_diff)
    os.execvpe(args.command[0], args.command, environ)
