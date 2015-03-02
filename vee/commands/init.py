from vee.commands.main import command, argument, main
from vee.home import PRIMARY_REPO
from vee.requirement import Requirement
from vee.utils import style


@command(
    argument('--name', default=PRIMARY_REPO, help='name for new repository'),
    argument('url', nargs='?', help='URL of new repository'),
    help='initialize VEE\'s home',
    usage='vee init URL',
)
def init(args):

    home = args.assert_home()
    home.makedirs()

    con = home.db.connect()
    row = con.execute('SELECT id FROM repositories WHERE name = ?', [args.name]).fetchone()

    print style('%sInitializing "%s"' % ('Re-' if row else '', args.name), 'blue', bold=True), home.root

    if not args.url:
        return
    
    if row:
        con.execute('UPDATE repositories SET url = ? WHERE id = ?', [args.url, row['id']])
    else:
        con.execute('INSERT INTO repositories (name, url, is_default) VALUES (?, ?, ?)', [args.name, args.url, True])
