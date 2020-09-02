import collections
import re

from vee.semver import Version


class Provides(collections.MutableMapping):

    def __init__(self, input_):

        self._data = {}

        if isinstance(input_, str):
            self._parse(input_)

        elif isinstance(input_, dict):
            self.update(input_)

        else:
            raise TypeError("provisions must be str or dict; got {}".format(type(input_)))

    def _parse(self, raw):

        for chunk in raw.split(','):
            chunk = chunk.strip()

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

