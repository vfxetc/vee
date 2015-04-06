from vee.commands.main import command, argument
from vee.network import Server

@command(
    argument('host', default=''),
    argument('port', type=int, default=38123),
)
def server(args):

    s = Server((args.host, args.port))
    s.run_forever()
