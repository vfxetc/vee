import argparse
import re
import shlex



class Requirement(object):

    arg_parser = argparse.ArgumentParser(add_help=False)
    arg_parser.add_argument('specification')

    @classmethod
    def parse(cls, args):

        if isinstance(args, basestring):
            args = shlex.split(args)
        if isinstance(args, (list, tuple)):
            args = cls.arg_parser.parse_args(args)

        return cls(args.specification)

    def __init__(self, spec):
        
        self.manager = None
        self.package = None

        # Extract the manager type. Usually this is of the form:
        # type+specification. Otherwise we assume it is a simple URL or file.
        m = re.match(r'^(\w+)\+(.+)$', spec)
        if m:
            self.manager_name = m.group(1)
            self.spec = m.group(2)
        elif re.match(r'^https?://', spec):
            self.manager_name = 'http'
            self.spec = spec
        else:
            self.manager_name = 'file'
            self.spec = spec

    def __str__(self):
        return (
            (self.manager_name + '+' if self.manager_name else '') +
            self.spec
        )

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def load(self):
        pass
