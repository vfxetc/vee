import json
import os
import re

from vee.cli import style, style_error, style_note, style_warning
from vee.commands.main import command, argument, group
from vee.envvars import render_envvars
from vee.exceptions import AlreadyInstalled
from vee.git import GitRepo
from vee.packages.git import normalize_git_url
from vee.requirement import Requirement
from vee.requirementset import RequirementSet
from vee.utils import makedirs
from vee import log


def iter_availible_requirements(home):
    env_repo = home.get_env_repo()
    reqs = env_repo.requirement_set()
    for req in reqs.iter_git_requirements():
        # Make sure it is a Git package.
        url = normalize_git_url(req.url, prefix=False)
        if url:
            yield req, url


@command(
    aliases=['dev'],
    help='develop a package',
    usage="""
       vee develop init [NAME]
   or: vee develop clone URL [NAME]
   or: vee develop add PATH [NAME]
   or: vee develop find PATH
   or: vee develop install NAME
   or: vee develop rescan [NAME ...]
   or: vee develop setenv NAME KEY=value [...]
   or: vee develop list [--availible] [--environ]
""".strip(),
)
def develop(args):
    pass


@develop.subcommand(
    argument('-a', '--availible', action='store_true'),
    argument('-e', '--environ', dest='show_environ', action='store_true'),
    argument('glob', nargs='?'),
    name='list',
    help='list all installed or availible tools'
)
def list_(args):

    home = args.assert_home()

    if args.availible:
        for req, url in iter_availible_requirements(home):
            print style_note(req.name, str(req))
        return

    if args.glob:
        cur = home.db.execute('SELECT * FROM development_packages WHERE name GLOB ? ORDER BY lower(name)', [args.glob])
    else:
        cur = home.db.execute('SELECT * FROM development_packages ORDER BY lower(name)')

    for row in cur:
        path = row['path'].replace(home.dev_root, '$VEE_DEV').replace(home.root, '$VEE')
        print style_note(row['name'], path)
        if args.show_environ:
            for k, v in sorted(render_envvars(json.loads(row['environ']), row['path']).iteritems()):
                if os.environ.get(k):
                    v = v.replace(os.environ[k], '$' + k)
                v = v.replace(home.dev_root, '$VEE_DEV')
                v = v.replace(home.root, '$VEE')
                print style('    %s=' % k) + v


@develop.subcommand(
    argument('--force', action='store_true'),
    argument('--repo'),
    argument('--path'),
    argument('name'),
    help='install a tool that is managed by the default repository'
)
def install(args):
    return init(args, do_install=True)


@develop.subcommand(
    argument('--force', action='store_true'),
    argument('--path'),
    argument('url'),
    argument('name', nargs='?'),
    help='clone a remote git repository to develop',
)
def clone(args):
    if not args.name:
        name = os.path.basename(args.url)
        if name.endswith('.git'):
            name = name[:-4]
        args.name = name
    return init(args, do_clone=True)


@develop.subcommand(
    argument('-r', '--recursive', action='store_true', help='add any tools found under given path'),
    argument('--force', action='store_true'),
    argument('path'),
    argument('name', nargs='?'),
    help='track an existing checkout',
)
def add(args):
    args.name = args.name or os.path.basename(args.path)
    return init(args, do_add=True)


@develop.subcommand(
    argument('patterns', nargs='+'),
    help='stop tracking dev packages',
)
def rm(args):
    res = 0
    con = args.assert_home().db.connect()
    for pattern in args.patterns:
        cur = con.execute('DELETE FROM development_packages WHERE name GLOB ?', [pattern])
        if not cur.rowcount:
            print style_warning('No dev packages matching "%s"' % pattern)
            res = 1
    return res


@develop.subcommand(
    argument('--force', action='store_true'),
    argument('path'),
    help='recursively find existing checkouts',
)
def find(args):
    res = e = None
    for dir_path, dir_names, file_names in os.walk(os.path.abspath(args.path)):
        if '.git' in dir_names:
            dir_names[:] = []
            args.path = dir_path
            args.name = os.path.basename(dir_path)
            res = res or init(args, do_add=True, is_find=True)
    if e:
        raise RuntimeError('There were errors adding dev packages.')
    return res


@develop.subcommand(
    argument('names', nargs='*'),
    help='recursively find existing checkouts',
)
def rescan(args):

    home = args.assert_home()
    con = home.db.connect()

    args.force = True

    pairs = []

    if args.names:
        for name in args.names:
            row = con.execute('SELECT path FROM development_packages WHERE name = ?', [name]).fetchone()
            if not row:
                log.warning('No dev package named %s' % name)
                continue
            path = row[0]
            if not os.path.exists(path):
                log.warning('Dev package %s not longer exists at %s' % (name, path))
                continue
            pairs.append((name, path))
    else:
        pairs = list(con.execute('SELECT name, path FROM development_packages'))

    for name, path in pairs:
        args.name = name
        args.path = path
        init(args, do_add=True)


@develop.subcommand(
    argument('--force', action='store_true'),
    argument('--path'),
    argument('name'),
    help='init a new git repository'
)
def init(args, do_clone=False, do_install=False, do_add=False, is_find=False):

    do_init = not (do_clone or do_install or do_add)

    name = args.name
    home = args.assert_home()
    
    con = home.db.connect()

    # Make sure there are no other packages already, and clear out old ones
    # which no longer exist.
    for row in con.execute('SELECT * FROM development_packages WHERE name = ?', [name]):
        if not args.force and os.path.exists(os.path.join(row['path'], '.git')):
            if is_find:
                print style_note('"%s" already exists:' % name, row['path'])
                return
            else:
                print style_error('"%s" already exists:' % name, row['path'])
                return 1
        else:
            con.execute('DELETE FROM development_packages WHERE id = ?', [row['id']])

    path = os.path.abspath(args.path or os.path.join(home.dev_root, name))

    dev_repo = GitRepo(path)

    if do_init:
        print style_note('Initing %s' % dev_repo.work_tree)
        makedirs(dev_repo.work_tree)
        dev_repo.git('init')

    elif do_clone:
        print style_note('Cloning %s' % args.url)
        makedirs(dev_repo.work_tree)
        dev_repo.clone_if_not_exists(args.url)

    elif do_install:
        # Find an existing tool.
        # TODO: put more of this into EnvironmentRepo or RequirementSet
        env_repo = home.get_env_repo(args.repo)
        req_path = os.path.join(env_repo.work_tree, 'requirements.txt')
        reqs = RequirementSet(req_path)
        reqs.guess_names()
        for req in reqs.iter_requirements():
            if req.name.lower() == name.lower():
                # Make sure it is a Git package.
                url = normalize_git_url(req.url, prefix=False)
                if url:
                    break
        else:
            print style_error('Could not find git-based "%s" in "%s" repo.' % (name, env_repo.name))
            return 2
        print style_note('Found %s in %s' % (name, env_repo.name), str(req))
        makedirs(dev_repo.work_tree)
        dev_repo.clone_if_not_exists(url, shallow=False)

    elif do_add:
        print style_note('Adding %s from %s' % (name, path))

    if not os.path.exists(path):
        log.error('%s does not exist'%  path)
        return 1

    req = Requirement(['file:' + path], home=home)
    package = req.package
    package.package_name = package.build_name = path

    log.info('%s is a "%s" package' % (name, package.builder.type))

    package.builder.develop()

    print style_note('Linking dev package', name, path)
    con.execute('INSERT INTO development_packages (name, path, environ) VALUES (?, ?, ?)', [name, path, json.dumps(package.environ)])


@develop.subcommand(
    argument('name'),
    argument('envvars', nargs='+'),
    help='set envvars within the dev execution environment',
)
def setenv(args):
    
    home = args.assert_home()
    con = home.db.connect()
    
    row = con.execute('SELECT * FROM development_packages WHERE name = ?', [args.name]).fetchone()
    if not row:
        raise ValueError('unknown dev package %r' % args.name)

    environ = json.loads(row['environ'])

    for envvar in args.envvars:
        if re.match(r'^-\w+$', envvar):
            del environ[envvar[1:]]
        else:
            key, value = envvar.split('=', 1)
            environ[key] = value

    con.execute('UPDATE development_packages SET environ = ? WHERE id = ?', [json.dumps(environ), row['id']])

