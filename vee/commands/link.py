from vee.commands.main import command, argument
from vee.environment import Environment
from vee.requirement import Requirement
from vee.utils import style
from vee.exceptions import CliException, AlreadyInstalled


@command(
    argument('--raw', action='store_true', help='package is directory, not a requirement'),
    argument('environment'),
    argument('specification', nargs='...'),
    help='link a package',
    usage='vee link [--raw] ENVIRONMENT SPECIFICATION',
)
def link(args):

    args.assert_home()

    env = Environment(args.environment, home=args.home)

    if args.raw:
        for dir_ in args.package:
            print style('Linking', 'blue', bold=True), style(dir_, bold=True)
            env.link_directory(dir_)
        return

    lines = list(open(args.specification[0]))
    lines = [x.strip() for x in lines]
    lines = [x for x in lines if x and not x[0] == '#']
    while lines:
        line = lines.pop(0).strip()
        while lines and line.endswith('\\'):
            line = line[:-1] + ' ' + lines.pop(0)

        req = Requirement(line, home=args.home)
        try:
            req.install()
        except AlreadyInstalled:
            pass
        
        print style('Linking', 'blue', bold=True), style(str(req), bold=True)

        req.manager.link(env)
        


