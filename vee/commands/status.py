import re

from vee.cli import style, style_error, style_note
from vee.commands.main import command, argument
from vee.exceptions import CliException
from vee.git import GitRepo, normalize_git_url
from vee.utils import guess_name


@command()
def status(args):

    home = args.assert_home()

    req_repo = home.get_repo()
    req_repo.set.guess_names()

    # Grab all of the dev packages.
    dev_packages = {}
    for row in home.db.execute('SELECT * FROM dev_packages'):
        dev_repo = GitRepo(row['path'])
        if not dev_repo.exists:
            continue
        url = dev_repo.remotes()['origin']
        dev_packages[normalize_git_url(row['url'])] = row

    # Lets match everything up.
    matched_packages = []
    for req in req_repo.iter_requirements(home):

        pkg = req.package
        if pkg.type != 'git':
            continue
        pkg.resolve_existing()

        dev = dev_packages.pop(normalize_git_url(pkg.url), None)
        matched_packages.append((pkg.name, dev, req, pkg))

    for dev in dev_packages.itervalues():
        matched_packages.append((dev['name'], dev, None, None))

    if not matched_packages:
        print style_error('No packages found.')
        return 1

    for name, dev, req, pkg in sorted(matched_packages):

        print style_note('==> ' + name)
        print dev
        print req
        print pkg


