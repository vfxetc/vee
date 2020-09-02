from __future__ import print_function

import json
import os
import re
import sys

from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.envvars import guess_envvars, render_envvars
from vee.exceptions import NotInstalled
from vee.manifest import Requirements
from vee.packageset import PackageSet


@command(
    argument('--export', action='store_true', help='export the environment instead of executing in it'),
    argument('--prefix', action='store_true', help='print the prefixes that would be linked together'),

    argument('-R', '--requirements', action='append', help='requirements or requirements files to include; may be comma separated'),
    argument('-r', '--repo', action='append', dest='repos', help='a repo whose HEAD to include; defaults to the default repo'),
    argument('-e', '--environment', action='append', help='an environment to include'),

    argument('-d', '--dev', action='store_true', help='include the development environment'),
    argument('--bootstrap', action='store_true', help='restore a previous dev environment (in $VEE_EXEC_ARGS)'),

    argument('command', nargs='...', help='the command to run'),
    name='exec',
    help='execute in this environment',
    usage='vee exec (-r REQUIREMENTS | ENVIRONMENT) COMMAND [...]',
    group='workflow',
)
def exec_(args):
    """Construct an environment, and either export it or run a command in it.
    e.g.::

        # Run in the default repository.
        $ vee exec $command

        # Run within a given repository.
        $ vee exec --repo named_repo $command

        # Run within a named environment.
        $ vee exec -e named_environ $command

        # Run within a constructed runtime for a set of requirements.
        $ vee exec -r requirements.txt $command

        # Export the default environment.
        $ vee exec --export
        export LD_LIBRARY_PATH="/usr/local/vee/environments/primary/master/lib:$LD_LIBRARY_PATH"
        export PATH="/usr/local/vee/environments/primary/master/bin:$PATH"
        export PYTHONPATH="/usr/local/vee/environments/primary/master/lib/python2.7/site-packages"

    """


    home = args.assert_home()

    # TODO: seed these with the current values.
    repo_names = []
    env_names = []

    environ_diff = {}

    if args.bootstrap:
        bootstrap = os.environ['VEE_EXEC_ARGS'].split() if os.environ.get('VEE_EXEC_ARGS') else []
        # This is gross, but easier than building another parser. It does mean
        # that we expect this variable must be set by ourselves.
        while bootstrap:
            arg = bootstrap.pop(0)
            if arg in ('--dev', ):
                setattr(args, arg[2:], True)
            elif arg in ('--requirements', '--repo', '--environment'):
                v = getattr(args, arg[2:], None) or []
                v.append(bootstrap.pop(0))
                setattr(args, arg[2:], v)
            else:
                print('cannot bootstrap', arg, file=sys.stderr)

    if args.dev:
        # Store the original flags as provided so that --bootstrap can pick it back up.
        bootstrap = os.environ['VEE_EXEC_ARGS'].split() if os.environ.get('VEE_EXEC_ARGS') else []
        if '--dev' not in bootstrap:
            bootstrap.append('--dev')
        for attr in 'requirements', 'repo', 'environment':
            for value in getattr(args, attr, None) or ():
                bootstrap.append('--' + attr)
                bootstrap.append(value)
        environ_diff['VEE_EXEC_ARGS'] = ' '.join(bootstrap)

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
            print(path)
        return

    environ_diff.update(guess_envvars(paths))

    if args.dev:
        for pkg in home.iter_development_packages(exists=True, search=True):
            if pkg.environ:
                environ_diff.update(render_envvars(pkg.environ, pkg.work_tree, environ_diff))

    # Add the current virtualenv.
    venv = os.environ.get('VIRTUAL_ENV')
    if venv:
        environ_diff['PYTHONPATH'] = '%s:%s' % (
            os.path.join(venv, 'lib', 'python%d.%d' % sys.version_info[:2], 'site-packages'),
            environ_diff.get('PYTHONPATH', ''), # This is sloppy.
        )

    # More environment variables.
    command = args.command or []
    while command and re.match(r'^\w+=', command[0]):
        k, v = command.pop(0).split('=', 1)
        environ_diff[k] = v

    environ_diff['VEE_EXEC_PATH'] = ':'.join(paths)
    environ_diff['VEE_EXEC_REPO'] = ','.join(repo_names)
    environ_diff['VEE_EXEC_ENV'] = ','.join(env_names)
    environ_diff['VEE_EXEC_PREFIX'] = paths[0]

    # Print it out instead of running it.
    if args.export:
        for k, v in sorted(environ_diff.items()):
            existing = os.environ.get(k)

            if existing is not None and not k.startswith('VEE_EXEC'):
                v = v.replace(existing, '$' + k)

            print('export %s="%s"' % (k, v))
        return

    environ = os.environ.copy()
    environ.update(environ_diff)
    os.execvpe(args.command[0], args.command, environ)
