from select import select
import json
import re
import socket


class CommandStream(object):

    def __init__(self, parent, command, stream_id):
        self.parent = parent
        self.command = command
        self.stream_id = stream_id
        self.msg_counter = 0
        self.finished = False

    def send(self, **kwargs):
        kwargs.update(
            command=self.command,
            stream=self.stream_id,
            counter=self.msg_counter,
            finished=self.finished,
        )
        self.msg_counter += 1
        self.parent.send(**kwargs)

    def error(self, error, **kwargs):
        kwargs['type'] = 'error'
        kwargs['status'] = 'error'
        kwargs['error'] = error
        self.finished = True
        self.send(**kwargs)

    def request(self, **kwargs):
        kwargs['type'] = 'request'
        kwargs['status'] = 'ok'
        self.finished = True
        self.send(**kwargs)



class NetworkLayer(object):

    def __init__(self):
        self.preline_buffer = []
        self.line_buffer = []
        self.tag_format = '%s%%04d' % self.__class__.__name__[0]
        self.tag_count = 0
        self.streams = {}

    def get_tag(self):
        tag = self.tag_format % self.tag_count
        self.tag_count += 1
        return tag

    def send(self, **kwargs):
        self.socket.send(json.dumps(kwargs))
        self.socket.send('\n')

    def start_stream(self, command):
        tag = self.get_tag()
        stream = CommandStream(self, command, tag)
        self.streams[tag] = stream






    def fileno(self):
        return self.socket.fileno()

    def injest(self, chunk):
        lines = chunk.splitlines(True)
        if not lines:
            raise ValueError('nothing to injest')
        for line in lines:
            self.preline_buffer.append(line)
            if line.endswith('\n'):
                self.line_buffer.append(''.join(self.preline_buffer))
                self.preline_buffer = []
        return self.line_buffer


class Agent(NetworkLayer):

    def __init__(self, addr):
        super(Agent, self).__init__()
        self.addr = addr
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_socket()



class Server(Agent):

    def __init__(self, *args):
        super(Server, self).__init__(*args)
        self.clients = []

    def init_socket(self):
        self.socket.bind(self.addr)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.listen(5)

    def run_forever(self):
        while True:
            
            for client in self.clients:
                if client.line_buffer:
                    client.handle_one()

            self.clients = [c for c in self.clients if c.line_buffer or not c.closed]

            rlist = [self]
            rlist.extend(self.clients)
            rlist, _, _ = select(rlist, [], [])

            for obj in rlist:
                obj.do_read()

    def do_read(self):
        sock, addr = self.socket.accept()
        print('new connection from', addr)
        client = ServerClient(self, sock, addr)
        self.clients.append(client)


class ServerClient(NetworkLayer):

    def __init__(self, server, sock, addr):
        super(ServerClient, self).__init__()
        self.server = server
        self.socket = sock
        self.addr = addr
        self.closed = False

    def __repr__(self):
        return '<%s for %s:%s from %s:%s>' % (
            self.__class__.__name__,
            self.server.addr[0], self.server.addr[1],
            self.addr[0], self.addr[1],
        )

    def do_read(self):
        raw = self.socket.recv(16384)
        if raw:
            self.injest(raw)
            # print 'injested', repr(raw)
        else:
            self.closed = True

    def handle_one(self):
        line = self.line_buffer.pop(0)
        obj = json.loads(line)
        print('handle', json.dumps(obj, indent=4, sort_keys=True))



class Client(Agent):

    def __init__(self, home, addr):
        super(Client, self).__init__(addr)
        self.home = home

    def init_socket(self):
        self.socket.connect(self.addr)

    def run_forever(self):
        from vee import __about__
        self.send_command('hello',
            hostname=socket.gethostname(),
            version=__about__.__version__,
            revision=__about__.__revision__,
        )
        self.send_command('repos.set',
            repos=dict((repo.name, {
                'head': repo.head,
                'remotes': repo.remotes(),
            }) for repo in self.home.iter_env_repos()),
        )

