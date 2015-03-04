import os

from vee.commands.main import command, argument
from vee.exceptions import AlreadyInstalled
from vee.requirement import Requirement
from vee.requirementset import RequirementSet
from vee.git import GitRepo
from vee.utils import style, style_error, style_note, style_warning, makedirs
from vee.packages.git import normalize_git_url


@command(
    argument('--init', action='store_true'),
    argument('--path'),
    argument('name'),
    argument('url', nargs='?'),
    help='develop a package',
    usage='vee develop [--path PATH] NAME',
)
def develop(args):

    home = args.assert_home()

    name = args.name

    con = home.db.connect()
    row = home.db.execute('SELECT * FROM dev_packages WHERE name = ?', [args.name]).fetchone()

    # Get the path.
    if args.path:
        path = args.path
    elif row and os.path.exists(row['path']):
        path = row['path']
    else:
        if row:
            print style_warning('Previously developed "%s" does not exist:' % name, row['path'])
        path = os.path.join(home.dev_root, name)


    dev_repo = GitRepo(path)

    if not dev_repo.exists:

        if args.url:
            print style_note('Cloning %s' % args.url)
            makedirs(dev_repo.work_tree)
            dev_repo.clone_if_not_exists(args.url)

        elif args.init:
            print style_note('Initing %s' % dev_repo.work_tree)
            makedirs(dev_repo.work_tree)
            dev_repo.git('init')

        else:
            # TODO: Look through non-default repos.
            req_repo = home.get_repo()
            req_path = os.path.join(req_repo.work_tree, 'requirements.txt')
            reqs = RequirementSet(req_path)
            reqs.guess_names()
            for req in reqs.iter_requirements():
                if req.name.lower() == name.lower():
                    # Make sure it is a Git package.
                    url = normalize_git_url(req.url)
                    if url:
                        break
            else:
                print style_error('Could not find git-based "%s" in default repo.' % name)
                return 2
            print style_note('Found %s' % req)
            makedirs(dev_repo.work_tree)
            dev_repo.clone_if_not_exists(url, shallow=False)

    if row and row['path'] != path:
        print style_note('Updating dev package', name, path)
        con.execute('UPDATE dev_packages SET path = ? WHERE id = ?', [path, row['id']])
    elif not row:
        print style_note('Linking dev package', name, path)
        con.execute('INSERT INTO dev_packages (name, path) VALUES (?, ?)', [name, path])

    req = Requirement(['file:' + path], home=home)
    package = req.package
    package.package_name = package.build_name = path
    package.builder.develop()
    
