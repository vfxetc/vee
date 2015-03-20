import json
import os
import re

from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.envvars import guess_envvars, render_envvars
from vee.exceptions import NotInstalled
from vee.requirementset import RequirementSet


@command(
    argument('--export', action='store_true', help='export the environment instead of executing in it'),
    argument('--prefix', action='store_true', help='print the prefixes that would be linked together'),

    argument('-R', '--requirements', action='append', help='requirements or requirements files to include; may be comma separated'),
    argument('-r', '--repo', action='append', dest='repos', help='a repo whose HEAD to include; defaults to the default repo'),
    argument('-e', '--environment', action='append', help='an environment to include'),

    argument('-d', '--dev', action='store_true', help='include the development environment'),

    argument('command', nargs='...', help='the command to run'),
    name='exec',
    help='execute in this environment',
    usage='vee exec (-r REQUIREMENTS | ENVIRONMENT) COMMAND [...]',
)
def exec_(args):

    home = args.assert_home()

    if not (args.export or args.command or args.prefix):
        raise ValueError('Must either --prefix, --export, or provide a command')

    # Default to the default repo.
    if not (args.requirements or args.environment or args.repos):
        args.repos = [None]
    
    paths = []

    # Named (or default) repos.
    for name in args.repos or ():
        repo = home.get_env_repo(name or None) # Allow '' to be the default.
        args.environment = args.environment or []
        args.environment.append('%s/%s' % (repo.name, repo.branch_name))

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
            raise NotInstalled(str(req))
        paths.append(req.package.install_path)

    # Named environments.
    for name in args.environment or ():
        env = Environment(name, home=home)
        paths.append(env.path)

    if args.prefix:
        for path in paths:
            print path
        return

    development_packages = []
    if args.dev:
        for pkg in home.db.execute('SELECT * FROM development_packages'):
            path = pkg['path']
            if os.path.exists(path):
                paths.append(path)
                development_packages.append(pkg)

    environ_diff = guess_envvars(paths)

    for pkg in development_packages:
        pkg_environ = json.loads(pkg['environ'])
        if pkg_environ:
            environ_diff.update(render_envvars(pkg_environ, pkg['path'], environ_diff))

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
