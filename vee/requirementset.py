import re

from vee.requirement import Requirement


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


class Header(tuple):

    def __new__(cls, name, value):
        name = '-'.join(x.title() for x in name.split('-'))
        return super(Header, cls).__new__(cls, (name, value))

    @property
    def name(self):
        return self[0]

    @property
    def value(self):
        return self[1]

    def __str__(self):
        return '%s: %s' % self


class RequirementSet(object):

    def __init__(self, source=None):
        self.elements = []
        if source:
            self.parse(source)

    def parse(self, source, home=None):
        
        if isinstance(source, basestring):
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
                self.elements.append((before, '', after))
                continue

            m = re.match(r'^(\w+)=(\S.*)$', spec)
            if m:
                self.elements.append((before, Envvar(*m.groups()), after))
                continue

            m = re.match(r'^([\w-]+): (\S.*)$', spec)
            if m:
                self.elements.append((before, Header(*m.groups()), after))
                continue

            self.elements.append((before, Requirement(spec, home=home), after))

    def dump(self):
        for before, element, after in self.elements:
            yield '%s%s%s\n' % (before, element, after)


if __name__ == '__main__':

    import sys

    from vee.home import Home

    home = Home('/usr/local/vee')
    rs = RequirementSet()
    rs.parse(sys.stdin, home=home)

    for b, r, a in rs.elements:
        print '%s%s%s' % (b, str(r) if r else '', a)

    print

    for b, e, a in rs.elements:
        if isinstance(e, Requirement):
            e.package.resolve_existing()
            frozen_req = e.package.freeze()
            print '%s%s%s' % (b, frozen_req, a)
        else:
            print '%s%s%s' % (b, e, a)


