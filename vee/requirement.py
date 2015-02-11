import argparse
import re
import shlex


class Requirement(object):

    arg_parser = argparse.ArgumentParser(add_help=False)
    arg_parser.add_argument('--name', default=None)
    arg_parser.add_argument('--revision', default=None)
    arg_parser.add_argument('package')


    def __init__(self, args, home=None):

        if isinstance(args, basestring):
            args = shlex.split(args)
        if isinstance(args, (list, tuple)):
            args = self.arg_parser.parse_args(args)
            
        # Extract the manager type. Usually this is of the form:
        # type+specification. Otherwise we assume it is a simple URL or file.
        m = re.match(r'^(\w+)\+(.+)$', args.package)
        if m:
            self.manager_name = m.group(1)
            self.package = m.group(2)
        elif re.match(r'^https?://', args.package):
            self.manager_name = 'http'
            self.package = args.package
        else:
            self.manager_name = 'file'
            self.package = args.package

        self._args = args
        self.home = home or args.home
        self.manager = self.home.get_manager(requirement=self)
        self.name = args.name
        self.revision = args.revision

    def __str__(self):
        package = self.manager_name + ('+' if self.manager_name else '') + self.package
        args = []
        if self.name:
            args.append('--name %s' % self.name)
        if self.revision:
            args.append('--revision %s' % self.revision)
        return package + (' ' if args else '') + ' '.join(sorted(args))

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))


    def install(self):
        self.manager.fetch()
        self.manager.extract()
        self.manager.build()
        self.manager.install()


