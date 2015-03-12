import re

from vee.requirement import Requirement, requirement_parser, RequirementParseError
from vee.utils import guess_name


class Envvar(tuple):

    def __new__(cls, name, value):
        return super(Envvar, cls).__new__(cls, (name, value))

    @property
    def name(self):
        return self[0]

    @property
    def value(self):
        return self[1]

    def __str__(self):
        return '%s=%s' % self


class Header(object):

    def __init__(self, name, value):
        self.name = '-'.join(x.title() for x in name.split('-'))
        self.value = value

    def __str__(self):
        return '%s: %s' % (self.name, self.value)


class RequirementSet(list):

    def __init__(self, source=None, home=None):

        self.home = home
        self._cumulative_environ = {}
        self.headers = {}

        if isinstance(source, (list, tuple)):
            self.parse_args(source)
        elif source:
            self.parse_file(source)

    def parse_args(self, args):

        remaining = args
        while remaining:
            args, remaining = requirement_parser.parse_known_args(remaining)
            if args.url.endswith('.txt'):
                self.parse_file(args.url)
            else:
                self.append(('', Requirement(args, home=self.home), ''))

    def parse_file(self, source):
        
        if source == '-':
            source = sys.stdin
        elif isinstance(source, basestring):
            source = open(source, 'r')

        line_iter = iter(source)
        for line in line_iter:

            line = line.rstrip()
            while line.endswith('\\'):
                line = line[:-1] + next(line_iter).rstrip()

            m = re.match(r'^(\s*)([^#]*?)(\s*#.*)?$', line)
            before, spec, after = m.groups()
            before = before or ''
            after = after or ''

            if not spec:
                self.append((before, '', after))
                continue

            m = re.match(r'^(\w+)=(\S.*)$', spec)
            if m:
                name, value = m.groups()
                self._cumulative_environ[name] = value
                self.append((before, Envvar(name, value), after))
                continue

            m = re.match(r'^([\w-]+): (\S.*)$', spec)
            if m:
                header = Header(*m.groups())
                self.headers[header.name] = header
                self.append((before, header, after))
                continue

            try:
                req = Requirement(spec, home=self.home)
            except RequirementParseError as e:
                self.append(('', '', '# RequirementParseError: %s' % e.args))
                self.append(('', '', '# ' + line.strip()))
                continue

            for k, v in self._cumulative_environ.iteritems():
                req.environ.setdefault(k, v)
            self.append((before, req, after))

    def iter_requirements(self):
        for _, element, _ in self:
            if isinstance(element, Requirement):
                yield element

    def iter_git_requirements(self):
        for req in self.iter_requirements():
            if req.package.type == 'git':
                yield req
    
    def guess_names(self, strict=True):
        """Guess names for every requirement which does not already have one.

        This mutates the requirements as it goes; if it fails then some
        requirements will have already had their name set.

        """

        names = set()
        to_guess = []

        # First pass: the explicitly named.
        for req in self.iter_requirements():

            if not req.name:
                to_guess.append(req)
                continue

            if req.name.lower() in names:
                raise ValueError('name collision; please rename one of the %rs' % name)
            names.add(req.name.lower())

        # Second pass; the rest.
        for req in to_guess:
            name = guess_name(req.url)
            if name.lower() in names:
                if strict:
                    raise ValueError('name collision; please set name for one of the %rs' % name)
            else:
                names.add(name.lower())
                req.name = name

    def iter_dump(self, freeze=False):

        # We track the state of the environment as we progress, and don't
        # include envvars in each requirement if they exactly match those
        # in the current state.
        environ = {}

        for before, element, after in self:

            if isinstance(element, Envvar):
                environ[element.name] = element.value

            if isinstance(element, Requirement):
                if freeze:
                    req = element = element.package.freeze(environ=False)
                else:
                    req = element
                for k, v in environ.iteritems():
                    if req.environ.get(k) == v:
                        del req.environ[k]

            yield '%s%s%s\n' % (before or '', element, after or '')



if __name__ == '__main__':

    import sys

    from vee.home import Home

    reqs = RequirementSet(sys.argv[1:], home=Home('/usr/local/vee'))
    reqs.guess_names()
    print ''.join(reqs.iter_dump())



