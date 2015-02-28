from vee.commands.main import command, argument
from vee.utils import style


@command(
    argument('--ping', action='store_true', help='print "pong"'),
    help='perform a self-check',
)
def doctor(args):

    if args.ping:
        print 'pong'
        return

    print style('Warning:', 'yellow', bold=True), 'Doctor isn\'t actually implemented yet.'
