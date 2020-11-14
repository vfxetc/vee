import collections
import re

from vee.semver import VersionExpr


class RequirementSet(collections.MutableMapping):

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
            raise TypeError("requirements must be str or dict; got {}".format(type(input_)))

    def parse(self, raw):

        for chunk in raw.split(';'):

            chunk = chunk.strip()
            if not chunk:
                continue
            
            # Just a name means we only care about presence.
            m = re.match(r'^\w+$', chunk)
            if m:
                self[chunk] = {}
                continue

            # Shortcut for version.
            m = re.match(r'^(\w+)([^\w:].+)$', chunk)
            if m:
                name, raw_expr = m.groups()
                self[name.strip()] = {'version': raw_expr.strip()}
                continue

            m = re.match(r'^(\w+):(.+)$', chunk)
            if m:
                name, rest = m.groups()
                self[name.strip()] = rest
                continue

            raise ValueError("could not parse requirement {!r}".format(chunk))

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
        self._data[key] = Requirement(value)

    def __delitem__(self, key):
        del self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __str__(self):

        out = []

        for name, reqs in self._data.items():

            if reqs:

                # Shortcut for version.
                if len(reqs) == 1 and 'version' in reqs:
                    out.append('{}{}'.format(name, reqs['version']))

                # Long format.
                else:
                    out.append('{}:{}'.format(name, reqs))

            # Only presense.
            else:
                out.append(name)

        return ';'.join(out)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(str(self)) if self else '')

    def __json__(self):
        return self._data



class Requirement(collections.MutableMapping):

    def __init__(self, input_=None):

        self._data = {}

        if isinstance(input_, str):
            self.parse(input_)

        elif isinstance(input_, dict):
            self.update(input_)

        elif input_ is not None:
            raise TypeError("requirements must be str or dict; got {}".format(type(input_)))

    def parse(self, raw):

        for chunk in raw.split(','):
            chunk = chunk.strip()

            # Just a name is for presence.
            m = re.match(r'^\w+$', chunk)
            if m:
                self.setdefault(chunk, None)
                continue

            m = re.match(r'^(\w+)(.+)$', chunk)
            if m:
                key, raw_expr = m.groups()
                self[key.strip()] = raw_expr.strip()
                continue

            raise ValueError("could not parse requirement {!r}".format(chunk))

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = None if value is None else VersionExpr.coerce(value)

    def __delitem__(self, key):
        del self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __str__(self):
        out = []
        for key, expr in self._data.items():
            out.append('{}{}'.format(key, expr))
        return ','.join(out)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(str(self)) if self else '')

    def __json__(self):
        return self._data

