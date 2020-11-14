import collections
import re

from vee.semver import Version


class Provision(collections.MutableMapping):

    @classmethod
    def coerce(cls, input_):
        return input_ if isinstance(input_, cls) else cls(input_)
    
    def __init__(self, input_=None):

        self._data = {}

        if isinstance(input_, str):
            if input_:
                self.parse(input_)

        elif isinstance(input_, dict):
            self.update(input_)

        elif input_ is not None:
            raise TypeError("provisions must be str or dict; got {}".format(type(input_)))

    def parse(self, raw):

        for chunk in raw.split(','):
            
            chunk = chunk.strip()
            if not chunk:
                continue

            # Just a name means we only care about presence.
            m = re.match(r'^\w+$', chunk)
            if m:
                self.setdefault(chunk, None)
                continue

            m = re.match(r'^(\w+)\s*=\s*(.+)$', chunk)
            if m:
                name, value = m.groups()
                self[name] = value.strip()
                continue

            raise ValueError("could not parse provision {!r}".format(chunk))

    def update(self, *args, **kwargs):
        for arg in args:
            if isinstance(arg, str):
                self.parse(arg)
            else:
                super().update(arg)
        if kwargs:
            super().update(kwargs)
    
    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = None if value is None else Version.coerce(value)

    def __delitem__(self, key):
        del self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __str__(self, sort=False):
        out = []
        for key, version in self._data.items():
            out.append('{}={}'.format(key, version))
        if sort:
            out.sort()
        return ','.join(out)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(str(self)) if self._data else '')

    def satisfies(self, reqs):

        for key, expr in reqs.items():

            try:
                value = self._data[key]
            except KeyError:
                return False

            if not expr.eval(value):
                return False

        return True


