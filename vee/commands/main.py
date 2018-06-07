"""VEE is a manager of versioned execution environments.

See: `vee COMMAND --help` for more on individual commands.

"""

import argparse
import cProfile
import errno
import functools
import logging
import os
import pkg_resources
import sys
import traceback

from vee import log
from vee.cli import style
from vee.exceptions import cli_exc_str, cli_errno, print_cli_exc
from vee.home import Home
from vee.utils import default_home_path
from vee.lockfile import RLockfile


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

    # This used to be a thing when it was possible for the home to not exist
    # because $VEE was not set.
    def assert_home(self):
        return self.home

    @property
    def home(self):
        try:
            return self._home
        except AttributeError:
            self._home = home = Home(self.home_path)
            return home

    @property
    def main(self):
        return self.home.main


_parser = None

def get_parser():

    global _parser

    if _parser:
        return _parser

    _parser = parser = argparse.ArgumentParser(
        prog='vee',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
        #usage='vee [-h] [-v] COMMAND ...',
    )

    parser.register('action', 'parsers', AliasedSubParsersAction)

    parser.add_argument('-v', '--verbose', action='count', default=0, help='increase verbosity; may be used multiple times')
    parser.add_argument('--log', help='dump complete log to file')
    parser.add_argument('--profile', dest='cprofile_path', help='dump execution profile to disk')
    parser.add_argument('--real-prefix', default=os.environ.get('VEE_REAL_PREFIX'),
        help="Force a value for sys.real_prefix.")

    parser.add_argument('--home',
        dest='home_path',
        metavar='VEE',
        help="path of managed environments; defaults to $VEE or the directory above VEE's source"
    )

    funcs = [ep.load() for ep in pkg_resources.iter_entry_points('vee_commands')]
    populate_subparser(parser, funcs)

    return parser



def trim_docstring(docstring):

    if not docstring:
        return ''

    lines = docstring.expandtabs().splitlines()

    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))

    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxint:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())

    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)

    return '\n'.join(trimmed)


def populate_subparser(parent_parser, funcs, depth=0):

    parent_parser._func_groups = groups = []
    groups_by_name = {}
    for group_name in 'setup', 'workflow', 'development':
        group = []
        groups.append((group_name, group))
        groups_by_name[group_name] = group

    # Group them by name.
    for func in funcs:
        func_help = func.__command_spec__[1].get('help')
        if not help:
            continue
        group_name = func.__command_spec__[1].pop('group', 'the rest')
        if group_name not in groups_by_name:
            group = []
            groups.append((group_name, group))
            groups_by_name[group_name] = group
        func_name = func.__command_spec__[1].get('name', func.__name__)
        groups_by_name[group_name].append((func_name, func))

    # Filter out empty groups.
    groups[:] = [(n, f) for n, f in groups if f]

    # Build up all the help. This is a little silly to do in advance, but... meh.
    help_chunks = []
    for group_name, group_funcs in groups:
        did_header = False
        for func_name, func in sorted(group_funcs):
            func_help = func.__command_spec__[1].get('help')
            if func_help is argparse.SUPPRESS or not func_help:
                continue
            if not did_header:
                if len(groups) > 1:
                    help_chunks.append('')
                    help_chunks.append('%s:' % group_name)
                did_header = True
            help_chunks.append('  %-12s %s' % (func_name, func_help))

    parent_subparser = parent_parser.add_subparsers(
        help=argparse.SUPPRESS,
        title='subcommands',
        description='\n'.join(help_chunks),
    )

    funcs.sort(key=lambda f: f.__command_spec__[1].get('name', f.__name__))

    for func in funcs:

        args, kwargs = func.__command_spec__
        func.__parse_known_args = kwargs.pop('parse_known_args', False)
        func.__acquire_lock = kwargs.pop('acquire_lock', False)
        add_verbose = kwargs.pop('add_verbose', True)

        name = kwargs.pop('name', func.__name__)
        kwargs.setdefault('aliases', [])
        kwargs.setdefault('formatter_class', argparse.RawDescriptionHelpFormatter)
        kwargs.setdefault('description', trim_docstring(func.__doc__))
        kwargs.setdefault('conflict_handler', 'resolve')

        parser = parent_subparser.add_parser(name, **kwargs)
        parser.set_defaults(**{'func%d' % depth: func})
        parser.register('action', 'parsers', AliasedSubParsersAction)

        if add_verbose:
            parser.add_argument('-v', '--verbose', action='count', default=0, help='increase verbosity; may be used multiple times')

        subcommands = getattr(func, '__subcommands__', None)
        if subcommands:
            populate_subparser(parser, subcommands, depth + 1)

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


class _LogFormatter(logging.Formatter):

    def format(self, record):
        msg = super(_LogFormatter, self).format(record)
        return msg.encode('string-escape')


_global_locks = {}


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
        args.home_path = default_home_path(environ=args.environ)
        
        if args.real_prefix and args.real_prefix != getattr(sys, 'real_prefix', None):
            sys.real_prefix = args.real_prefix

        if args.log:
            root = logging.getLogger('vee')
            stream = sys.stdout if args.log == '-' else open(args.log, 'ab')
            handler = logging.StreamHandler(stream)

            handler.setFormatter(_LogFormatter('%(asctime)-15s %(name)s %(levelname)s: %(message)s'))
            root.addHandler(handler)

        # When called recursively, we want to maintain at least the previous
        # level of verbosity.
        log.config.verbosity = max(log.config.verbosity, args.verbose or 0)

        # TODO: Move this to a $VEE_UMASK envvar or something.
        # For now, just leave all permissions open.
        os.umask(0)

        if func:
            lock = None
            try:
                # Don't grab the lock if we dont need it (or if the home isn't set)
                if func.__acquire_lock and args.home_path and os.path.exists(args.home_path):
                    try:
                        lock = _global_locks[args.home_path]
                    except KeyError:
                        lock_content = (
                            os.environ.get('VEE_LOCK_CONTENT') or
                            '%s@%s/%s' % (os.getlogin(), os.environ.get('SSH_CLIENT', 'localhost').split()[0], os.getpid())
                        )
                        lock = RLockfile(os.path.join(args.home_path, '.vee-lock'), blocking=False, content=lock_content)
                        _global_locks[args.home_path] = lock
                    lock.acquire()
            except IOError as e:
                if e.errno == errno.EWOULDBLOCK:
                    content = lock.get_content()
                    log.error('VEE is locked%s' % (': ' + content if content else '', ))
                    res = 1
                else:
                    raise
            else:
                if args.cprofile_path:
                    res = cProfile.runctx('func(args, *unparsed)', locals(), globals(), filename=args.cprofile_path) or 0
                else:
                    res = func(args, *unparsed) or 0
                if func.__acquire_lock and lock is not None:
                    lock.release()

        else:
            parser.print_help()
            res = 1

    except Exception as e:
        if as_main:
            print_cli_exc(e, verbose=True)
            res = cli_errno(e)
        else:
            raise
    
    return res

