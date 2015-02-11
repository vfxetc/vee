import argparse
import re
import shlex


class Package(object):

    arg_parser = argparse.ArgumentParser(add_help=False)
    arg_parser.add_argument('--revision', default=None)
    arg_parser.add_argument('package_spec')

    @classmethod
    def parse(cls, args, **kwargs):
        if isinstance(args, basestring):
            args = shlex.split(args)
        if isinstance(args, (list, tuple)):
            args = cls.arg_parser.parse_args(args)
        return cls(args, **kwargs)

    def __init__(self, args, home=None):
        
        self._args = args
        self.revision = args.revision
        
        # Extract the manager type. Usually this is of the form:
        # type+specification. Otherwise we assume it is a simple URL or file.
        m = re.match(r'^(\w+)\+(.+)$', args.package_spec)
        if m:
            self.manager_name = m.group(1)
            self.spec = m.group(2)
        elif re.match(r'^https?://', args.package_spec):
            self.manager_name = 'http'
            self.spec = args.package_spec
        else:
            self.manager_name = 'file'
            self.spec = args.package_spec

        self.home = home or args.home
        self.manager = self.home.get_manager(package=self)

    def __str__(self):
        return (
            (self.manager_name + '+' if self.manager_name else '') +
            self.spec
        )

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def fetch(self):
        self.manager.fetch()

    def install(self):
        self.manager.install()


