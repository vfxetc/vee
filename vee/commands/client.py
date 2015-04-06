from vee.commands.main import command, argument
from vee.network import Client

@command(
    argument('host'),
    argument('port', type=int, default=38123),
)
def client(args):

    c = Client(args.assert_home(), (args.host, args.port))
    c.run_forever()
