"""VEE is a manager of versioned execution environments.

See: `vee <command> --help` for more on individual commands.

"""

import argparse
import cProfile
import os
import pkg_resources
import sys
import traceback

from vee.exceptions import CliException
from vee.home import Home
from vee.utils import style


class AliasedSubParsersAction(argparse._SubParsersAction):
 
    def add_parser(self, name, **kwargs):
        aliases = kwargs.pop('aliases', [])
        parser = super(AliasedSubParsersAction, self).add_parser(name, **kwargs)
        for alias in aliases:
            pass # self._name_parser_map[alias] = parser
        return parser


def argument(*args, **kwargs):
    return args, kwargs

def group(*args, **kwargs):
    kwargs['__type__'] = 'group'
    return args, kwargs


def command(*args, **kwargs):
    def _decorator(func):
        func.__command_spec__ = (args, kwargs)
        return func
    return _decorator



class Namespace(argparse.Namespace):

    def assert_home(self):
        if not self.home:
            raise CliException('please set $VEE or use --home')
        return self.home



_parser = None

def get_parser():

    global _parser

    if _parser:
        return _parser

    _parser = parser = argparse.ArgumentParser(
        prog='vee',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
        usage='vee [-h] COMMAND [ARGS]',
    )

    parser.register('action', 'parsers', AliasedSubParsersAction)
    subparsers = parser.add_subparsers(metavar='COMMAND')

    parser.add_argument('--home',
        dest='home_path',
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
            if arg_kwargs.pop('__type__', None) == 'group':
                if arg_kwargs.pop('exclusive', False):
                    group = subparser.add_mutually_exclusive_group(**arg_kwargs)
                else:
                    group = subparser.add_argument_group(**arg_kwargs)
                for arg_args, arg_kwargs in arg_args:
                    group.add_argument(*arg_args, **arg_kwargs)
            else:
                subparser.add_argument(*arg_args, **arg_kwargs)

    return parser


def main(argv=None, environ=None, as_main=__name__=="__main__"):

    parser = get_parser()

    args, unparsed = parser.parse_known_args(argv, namespace=Namespace())
    if args.func and unparsed and not args.func.__parse_known_args:
        args = parser.parse_args(argv, namespace=Namespace())

    args.environ = os.environ if environ is None else environ
    args.home_path = args.home_path or args.environ.get('VEE')
    

    args.home = args.home_path and Home(args.home_path)
    args.main = getattr(args.home, 'main')
    

    if args.func:
        try:
            res = args.func(args, *unparsed) or 0
        except Exception as e:
            if as_main:
                if isinstance(e, CliException):
                    print e.clistr
                    res = e.errno
                else:
                    stack = traceback.format_list(traceback.extract_tb(sys.exc_traceback))
                    print style(''.join(stack).rstrip(), faint=True)
                    print style(e.__class__.__name__ + ':', 'red', bold=True), style(str(e), bold=True)
                    res = 1
            else:
                raise
    else:
        parser.print_help()
        res = 1
    
    return res

