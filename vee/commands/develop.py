import json
import os

from vee.cli import style, style_error, style_note, style_warning
from vee.commands.main import command, argument, group
from vee.envvars import render_envvars
from vee.exceptions import AlreadyInstalled, CliException
from vee.git import GitRepo
from vee.packages.git import normalize_git_url
from vee.requirement import Requirement
from vee.requirementset import RequirementSet
from vee.utils import makedirs


def iter_availible_requirements(home):
    req_repo = home.get_repo()
    req_path = os.path.join(req_repo.work_tree, 'requirements.txt')
    reqs = RequirementSet(req_path)
    reqs.guess_names()
    for req in reqs.iter_requirements():
        # Make sure it is a Git package.
        url = normalize_git_url(req.url, prefix=False)
        if url:
            yield req, url


@command(
    aliases=['dev'],
    help='develop a package',
    usage="vee develop (list|init|clone|install) [ARGS]",
)
def develop(args):
    pass


@develop.subcommand(
    argument('-a', '--availible', action='store_true'),
    argument('-e', '--environ', dest='show_environ', action='store_true'),
    help='list dev packages'
)
def list(args):

    home = args.assert_home()

    if args.availible:
        for req, url in iter_availible_requirements(home):
            print style_note(req.name, str(req))
        return

    for row in home.db.execute('SELECT * FROM dev_packages ORDER BY name'):
        path = row['path'].replace(home.dev_root, '$VEE_DEV').replace(home.root, '$VEE')
        print style_note(row['name'], path)
        if args.show_environ:
            for k, v in sorted(render_envvars(json.loads(row['environ']), row['path']).iteritems()):
                v = v.replace(home.dev_root, '$VEE_DEV')
                v = v.replace(home.root, '$VEE')
                if os.environ.get(k):
                    v = v.replace(os.environ[k], '$' + k)
                print style('    %s=' % k) + v


@develop.subcommand(
    argument('--force', action='store_true'),
    argument('--path'),
    argument('name'),
)
def install(args):
    return init(args, do_install=True)


@develop.subcommand(
    argument('--force', action='store_true'),
    argument('--path'),
    argument('url'),
    argument('name', nargs='?'),
)
def clone(args):
    if not args.name:
        name = os.path.basename(args.url)
        if name.endswith('.git'):
            name = name[:-4]
        args.name = name
    return init(args, do_clone=True)


@develop.subcommand(
    argument('--force', action='store_true'),
    argument('--path'),
    argument('name'),
)
def init(args, do_clone=False, do_install=False):

    do_init = not (do_clone or do_install)

    name = args.name
    home = args.assert_home()
    
    con = home.db.connect()

    # Make sure there are no other packages already, and clear out old ones
    # which no longer exist.
    for row in con.execute('SELECT * FROM dev_packages WHERE name = ?', [name]):
        if not args.force and os.path.exists(os.path.join(row['path'], '.git')):
            print style_error('"%s" already exists:' % name, row['path'])
            return 1
        else:
            con.execute('DELETE FROM dev_packages WHERE id = ?', [row['id']])

    path = args.path or os.path.join(home.dev_root, name)
    dev_repo = GitRepo(path)

    if do_init:
        print style_note('Initing %s' % dev_repo.work_tree)
        makedirs(dev_repo.work_tree)
        dev_repo.git('init')

    elif do_clone:
        print style_note('Cloning %s' % args.url)
        makedirs(dev_repo.work_tree)
        dev_repo.clone_if_not_exists(args.url)

    else:
        # Find an existing tool.
        req_repo = home.get_repo()
        req_path = os.path.join(req_repo.work_tree, 'requirements.txt')
        reqs = RequirementSet(req_path)
        reqs.guess_names()
        for req in reqs.iter_requirements():
            if req.name.lower() == name.lower():
                # Make sure it is a Git package.
                url = normalize_git_url(req.url, prefix=False)
                if url:
                    break
        else:
            print style_error('Could not find git-based "%s" in default repo.' % name)
            return 2
        print style_note('Found %s in %s' % (name, req_repo.name), str(req))
        makedirs(dev_repo.work_tree)
        dev_repo.clone_if_not_exists(url, shallow=False)

    req = Requirement(['file:' + path], home=home)
    package = req.package
    package.package_name = package.build_name = path
    package.builder.develop()

    print style_note('Linking dev package', name, path)
    con.execute('INSERT INTO dev_packages (name, path, environ) VALUES (?, ?, ?)', [name, path, json.dumps(package.environ)])


