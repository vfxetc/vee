"""VEE is a manager of versioned execution environments.

See: `vee <command> --help` for more on individual commands.

"""

import argparse
import cProfile
import os
import pkg_resources

from vee.home import Home
from vee.repo import Repo


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


class CommandError(EnvironmentError):
    pass


class Namespace(argparse.Namespace):

    def assert_home(self):
        if not self.home:
            raise CommandError(1, 'home is required; please set VEE_HOME or --home')

    def assert_repo(self):
        if not self.home:
            raise CommandError(1, 'repo is required; please set VEE_REPO or --repo')



def main(argv=None):

    parser = argparse.ArgumentParser(
        prog='vee',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
    )

    parser.register('action', 'parsers', AliasedSubParsersAction)
    subparsers = parser.add_subparsers(metavar='COMMAND')

    parser.add_argument('--home',
        dest='home_path',
        default=os.environ.get('VEE_HOME'),
        help='path of managed environments',
    )
    parser.add_argument('--repo',
        dest='repo_path',
        default=os.environ.get('VEE_REPO'),
        help='repository of environment specifications'
    )

    funcs = [ep.load() for ep in pkg_resources.iter_entry_points('vee_commands')]
    funcs.sort(key=lambda f: f.__command_spec__[1].get('name', f.__name__))

    for func in funcs:
        args, kwargs = func.__command_spec__
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

    args = parser.parse_args(argv, namespace=Namespace())
    args.repo = args.repo_path and Repo(args.repo_path)
    args.home = args.home_path and Home(args.home_path, args.repo)

    if args.func:
        try:
            res = args.func(args) or 0
        except CommandError as e:
            if e.strerror:
                print e.strerror
            res = e.errno
    else:
        parser.print_usage()
        res = 1
    

    if __name__ == '__main__':
        exit(res)
    else:
        return res

