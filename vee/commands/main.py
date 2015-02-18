"""VEE is a manager of versioned execution environments.

See: `vee <command> --help` for more on individual commands.

"""

import argparse
import cProfile
import os
import pkg_resources

from vee.home import Home
from vee.exceptions import CliException


class AliasedSubParsersAction(argparse._SubParsersAction):
 
    def add_parser(self, name, **kwargs):
        aliases = kwargs.pop('aliases', [])
        parser = super(AliasedSubParsersAction, self).add_parser(name, **kwargs)
        for alias in aliases:
            pass # self._name_parser_map[alias] = parser
        return parser


def argument(*args, **kwargs):
    return args, kwargs

def group(title, *args):
    return title, args

def command(*args, **kwargs):
    def _decorator(func):
        func.__command_spec__ = (args, kwargs)
        return func
    return _decorator



class Namespace(argparse.Namespace):

    def assert_home(self):
        if not self.home:
            raise CliException('please set $VEE or use --home')



def main(argv=None, environ=None):

    parser = argparse.ArgumentParser(
        prog='vee',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
        usage='vee [-h] COMMAND [ARGS]',
    )

    parser.register('action', 'parsers', AliasedSubParsersAction)
    subparsers = parser.add_subparsers(metavar='COMMAND')

    # Mainly for mocking.
    environ = os.environ if environ is None else environ

    parser.add_argument('--home',
        dest='home_path',
        default=environ.get('VEE'),
        help='path of managed environments',
    )

    funcs = [ep.load() for ep in pkg_resources.iter_entry_points('vee_commands')]
    funcs.sort(key=lambda f: f.__command_spec__[1].get('name', f.__name__))

    for func in funcs:
        args, kwargs = func.__command_spec__
        func.__parse_known_args = kwargs.pop('parse_known_args', False)
        name = kwargs.pop('name', func.__name__)
        kwargs.setdefault('aliases', [])
        kwargs.setdefault('formatter_class', argparse.RawDescriptionHelpFormatter)
        subparser = subparsers.add_parser(name, **kwargs)
        subparser.set_defaults(func=func)

        for arg_args, arg_kwargs in args:
            if isinstance(arg_args, basestring):
                group = subparser.add_argument_group(arg_args)
                for arg_args, arg_kwargs in arg_kwargs:
                    group.add_argument(*arg_args, **arg_kwargs)
            else:
                subparser.add_argument(*arg_args, **arg_kwargs)

    args, unparsed = parser.parse_known_args(argv, namespace=Namespace())
    if args.func and unparsed and not args.func.__parse_known_args:
        args = parser.parse_args(argv, namespace=Namespace())

    args.home = args.home_path and Home(args.home_path)

    if args.func:
        try:
            res = args.func(args, *unparsed) or 0
        except CliException as e:
            print e.clistr
            res = e.errno
    else:
        parser.print_help()
        res = 1
    

    if __name__ == '__main__':
        exit(res)
    else:
        return res

