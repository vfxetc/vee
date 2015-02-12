import os

from vee.commands.main import command, argument
from vee.environment import Environment


@command(
    argument('environment'),
    argument('command', nargs='...'),
    name='exec',
    help='execute in this environment',
    usage='vee exec ENVIRONMENT',
)
def exec_(args):
    args.assert_home()
    env = Environment(args.environment, home=args.home)
    environ = os.environ.copy()
    environ.update(env.get_environ())
    os.execvpe(args.command[0], args.command, environ)
