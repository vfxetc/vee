import collections

from vee.utils import cached_property


class Config(collections.MutableMapping):

    def __init__(self, home):
        self._home = home
        self._db = home.db

    @property
    def exists(self):
        return self._db.exists

    @cached_property
    def _con(self):
        return self._db.connect()

    def _cursor(self):
        return self._con.cursor()

    def __getitem__(self, name):
        row = self._con.execute('SELECT value FROM config WHERE name = ?', [name]).fetchone()
        if row:
            return row[0]
        else:
            raise KeyError(name)

    def __setitem__(self, name, value):
        self._con.execute('INSERT OR REPLACE INTO config (name, value) values (?, ?)', [name, value])

    def __delitem__(self, name):
        cur = self._con.execute('DELETE FROM config WHERE name = ?', [name])
        if not cur.rowcount:
            raise KeyError(name)

    def __iter__(self):
        for row in self._con.execute('SELECT name FROM config'):
            yield row[0]

    def items(self, glob=None):
        if glob:
            cur = self._con.execute('SELECT name, value FROM config WHERE name GLOB ?', [glob])
        else:
            cur = self._con.execute('SELECT name, value FROM config')
        for row in cur:
            yield row[0], row[1]

    def __len__(self):
        row = self._con.execute('SELECT count(*) FROM config').fetchone()
        return row[0]
