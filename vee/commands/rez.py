from __future__ import print_function

import os
import re

from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.cli import style, style_note
from vee import log
from vee.package import Package
from vee.utils import makedirs


def rezify_name(x):
    return re.sub(r'\W+', '_', x).strip('_')

def create_package(pkg):

    print(pkg.name, pkg.revision, pkg.install_path)

    # Can't deal with hyphens
    name = rezify_name(pkg.name)

    # Strip off the homebrew commit.
    version = pkg.revision.split('+')[0]

    pkg_dir = os.path.join(pkg.home.root, 'packages', 'rez', 'packages', name, version)
    makedirs(pkg_dir)

    pkg_file = os.path.join(pkg_dir, 'package.py')

    requires = []
    for dep in pkg.dependencies:
        dep.resolve_existing()
        requires.append(rezify_name(dep.name))

    with open(pkg_file, 'w') as fh:

        fh.write('''

config_version = 0

name = {name!r}

version = {version!r}

requires = {requires!r}

def commands():
    pass

'''.format(**locals()))

        bin_ = os.path.join(pkg.install_path, 'bin')
        if os.path.exists(bin_):
            fh.write('''
    env.PATH.append({!r})
'''.format(bin_))

        site_packages = "{pkg.install_path}/lib/python2.7/site-packages"
        if os.path.exists(site_packages):
            fh.write('''
    env.PYTHONPATH.append({!r})
'''.format(site_packages))




@command(

)
def rezpack(args):

    home = args.assert_home()
    con = home.db.connect()


    for row in con.execute('SELECT * from packages ORDER by created_at DESC'):


        pkg = Package(url='junk', home=home)
        pkg.restore_from_row(row)
        pkg._load_dependencies()

        create_package(pkg)

