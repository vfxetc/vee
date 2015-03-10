"""VEE is a manager of versioned execution environments.

See: `vee <command> --help` for more on individual commands.

"""

import argparse
import cProfile
import functools
import os
import pkg_resources
import sys
import traceback

from vee.cli import style
from vee.exceptions import cli_exc_str, cli_errno, print_cli_exc
from vee.home import Home


class AliasedSubParsersAction(argparse._SubParsersAction):
 
    def add_parser(self, name, **kwargs):
        aliases = kwargs.pop('aliases', [])
        parser = super(AliasedSubParsersAction, self).add_parser(name, **kwargs)
        for alias in aliases:
            self._name_parser_map[alias] = parser
        return parser


def argument(*args, **kwargs):
    return args, kwargs

def group(*args, **kwargs):
    kwargs['__type__'] = 'group'
    return args, kwargs


def command(*args, **kwargs):
    def _decorator(func):
        func.__command_spec__ = (args, kwargs)
        func.__subcommands__ = []
        func.subcommand = functools.partial(subcommand, func)
        return func
    return _decorator

def subcommand(parent, *args, **kwargs):
    def _decorator(func):
        parent.__subcommands__.append(func)
        func.__command_spec__ = (args, kwargs)
        func.subcommand = functools.partial(subcommand, func)
        return func
    return _decorator


class Namespace(argparse.Namespace):

    def assert_home(self):
        if not self.home:
            raise RuntimeError('please set $VEE or use --home')
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
    command_subparser = parser.add_subparsers(metavar='COMMAND')

    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('--home',
        dest='home_path',
        metavar='VEE',
        help='path of managed environments',
    )

    funcs = [ep.load() for ep in pkg_resources.iter_entry_points('vee_commands')]

    populate_subparser(command_subparser, funcs)

    return parser


def populate_subparser(parent_subparser, funcs, depth=0):

    funcs.sort(key=lambda f: f.__command_spec__[1].get('name', f.__name__))

    for func in funcs:

        args, kwargs = func.__command_spec__
        func.__parse_known_args = kwargs.pop('parse_known_args', False)
        name = kwargs.pop('name', func.__name__)
        kwargs.setdefault('aliases', [])
        kwargs.setdefault('formatter_class', argparse.RawDescriptionHelpFormatter)

        parser = parent_subparser.add_parser(name, **kwargs)
        parser.set_defaults(**{'func%d' % depth: func})
        parser.register('action', 'parsers', AliasedSubParsersAction)

        subcommands = getattr(func, '__subcommands__', None)
        if subcommands:
            command_subparser = parser.add_subparsers(metavar='SUBCOMMAND')
            populate_subparser(command_subparser, subcommands, depth + 1)

        for arg_args, arg_kwargs in args:
            if arg_kwargs.pop('__type__', None) == 'group':
                if arg_kwargs.pop('exclusive', False):
                    group = parser.add_mutually_exclusive_group(**arg_kwargs)
                else:
                    group = parser.add_argument_group(**arg_kwargs)
                for arg_args, arg_kwargs in arg_args:
                    group.add_argument(*arg_args, **arg_kwargs)
            else:
                parser.add_argument(*arg_args, **arg_kwargs)


def get_func(args):
    depth = 0
    func = None
    while True:
        try:
            func = getattr(args, 'func%d' % depth)
        except AttributeError:
            return func
        else:
            depth += 1


def main(argv=None, environ=None, as_main=__name__=="__main__"):

    args = None

    try:

        parser = get_parser()

        args, unparsed = parser.parse_known_args(argv, namespace=Namespace())
        func = get_func(args)
        if func and unparsed and not func.__parse_known_args:
            args = parser.parse_args(argv, namespace=Namespace())
            func = get_func(args)

        args.environ = os.environ if environ is None else environ
        args.home_path = args.home_path or args.environ.get('VEE')
        

        args.home = args.home_path and Home(args.home_path)
        args.main = getattr(args.home, 'main', None)
        
        if func:
            res = func(args, *unparsed) or 0
        else:
            parser.print_help()
            res = 1

    except Exception as e:
        if as_main:
            print_cli_exc(e, verbose=args is None or args.verbose)
            res = cli_errno(e)
        else:
            raise
    
    return res

