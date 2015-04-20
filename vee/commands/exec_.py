import json
import os
import re

from vee._vendor import vendor_path, bootstrap_environ
from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.envvars import guess_envvars, render_envvars
from vee.exceptions import NotInstalled
from vee.packageset import PackageSet
from vee.requirements import Requirements


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

    repo_names = []
    env_names = []

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
        repo_names.append(repo.name)

    # Requirements and requirement sets.
    req_args = []
    for arg in args.requirements or ():
        req_args.extend(arg.split(','))
    req_set = Requirements(home=home)
    req_set.parse_args(req_args)
    pkg_set = PackageSet(home=home)
    for req in req_set.iter_packages():
        pkg = pkg_set.resolve(req)
        pkg._assert_paths(install=True)
        if not pkg.installed:
            raise NotInstalled(pkg.install_path)
        paths.append(pkg.install_path)

    # Named environments.
    for name in args.environment or ():
        env = Environment(name, home=home)
        paths.append(env.path)
        env_names.append(name)

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

    # Make sure setuptools is bootstrapped.
    bootstrap_environ(environ_diff)

    environ_diff['VEE_EXEC_PATH'] = ':'.join(paths)
    environ_diff['VEE_EXEC_REPO'] = ','.join(repo_names)
    environ_diff['VEE_EXEC_ENV'] = ','.join(env_names)
    environ_diff['VEE_EXEC_PREFIX'] = paths[0]

    # Print it out instead of running it.
    if args.export:
        for k, v in sorted(environ_diff.iteritems()):
            existing = os.environ.get(k)

            # Since we modify os.environ in __init__ to bootstrap the vendored
            # packages, swaping out the original values will not include the
            # bootstrap. So we are tricking the code so that it still includes it.
            if k == 'PYTHONPATH' and existing.endswith(vendor_path):
                existing += (':' if existing else '') + vendor_path

            if existing is not None and not k.startswith('VEE_EXEC'):
                v = v.replace(existing, '$' + k)
            print 'export %s="%s"' % (k, v)
        return

    environ = os.environ.copy()
    environ.update(environ_diff)
    os.execvpe(args.command[0], args.command, environ)
