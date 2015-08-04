import os

from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.cli import style, style_note
from vee import log
from vee.package import Package


def describe(pkg, cache, depth=0):

    print ('    ' * depth) + style(pkg.name, 'blue'), pkg.id, style(
        '***' if pkg.id in cache else str(pkg), faint=True)

    if pkg.id in cache:
        return
    cache[pkg.id] = pkg

    for dep in pkg.dependencies:
        dep.resolve_existing()
        describe(dep, cache, depth + 1)


@command(
    argument('-e', '--environments', action='store_true'),
    name='list',
)
def list_(args):


    if args.environments:
        list_environments(args)
        return
    else:
        list_packages(args)



def list_environments(args):

    home = args.assert_home()
    con = home.db.connect()

    cache = {}

    for env in con.execute('SELECT * from environments ORDER by created_at ASC'):
        print env['created_at'], style(env['name'], 'blue'), env['id']
        # print list(row)



def list_packages(args):

    home = args.assert_home()
    con = home.db.connect()

    cache = {}

    for row in con.execute('SELECT * from packages ORDER by created_at DESC'):

        if row['id'] in cache:
            continue

        pkg = Package(url='junk', home=home)
        pkg.restore_from_row(row)
        pkg._load_dependencies()

        describe(pkg, cache)

