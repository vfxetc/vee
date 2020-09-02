import collections
import re

from vee.semver import VersionExpr


class Requires(collections.MutableMapping):

    def __init__(self, input_):

        self._data = {}

        if isinstance(input_, str):
            self._parse_outer(input_)

        elif isinstance(input_, dict):
            self.update(input_)

        else:
            raise TypeError("requirements must be str or dict; got {}".format(type(input_)))

    def _parse_outer(self, raw):

        for chunk in raw.split(';'):
            chunk = chunk.strip()

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


    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = PackageRequires(value)

    def __delitem__(self, key):
        del self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __str__(self):

        out = []

        for key, value in self._data.items():
            if value:
                out.append('{}:{}'.format(key, value))
            else:
                out.append(key)

        return ';'.join(out)

    def __repr__(self):
        return 'Requires({!r})'.format(str(self))



class PackageRequires(collections.MutableMapping):

    def __init__(self, input_):

        self._data = {}

        if isinstance(input_, str):
            self._parse(input_)

        elif isinstance(input_, dict):
            self.update(input_)

        else:
            raise TypeError("requirements must be str or dict; got {}".format(type(input_)))

    def _parse(self, raw):

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

            raise ValueError("could not parse requirement {!r}; bad hunk {!r}".format(chunk, hunk))

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
        return 'Requires({!r})'.format(str(self))

