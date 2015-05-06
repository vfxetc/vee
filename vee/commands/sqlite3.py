import os

from vee.cli import style_error
from vee.commands.main import command, argument
from vee.subproc import call
from vee.utils import makedirs


@command(
    help='run a command in the database',
    parse_known_args=True,
    aliases=['sqlite'],
    acquire_lock=True,
)
def sqlite3(args, *command):
    home = args.assert_home()
    cmd = ['sqlite3', home.db.path]
    cmd.extend(command)
    os.execvp('sqlite3', cmd)
