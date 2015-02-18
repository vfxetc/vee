import contextlib
import datetime
import sqlite3


_migrations = []

def _migration(f):
    _migrations.append(f)

@_migration
def _create_initial_tables(con):
    con.execute('''CREATE TABLE installs (

        id INTEGER PRIMARY KEY,
        created_at TIMESTAMP NOT NULL,

        -- Requirement.__str__
        user_specification TEXT NOT NULL,

        manager TEXT NOT NULL,
        package TEXT NOT NULL,
        
        -- Attributes given by the user.
        name TEXT,

        -- Installed revision; either from the user or discovered.
        revision TEXT,

        -- Names, either from the user or discovered.
        package_name TEXT NOT NULL,
        build_name TEXT NOT NULL,
        install_name TEXT NOT NULL,

        -- Paths for direct lookup.
        package_path TEXT NOT NULL,
        build_path TEXT NOT NULL,
        install_path TEXT NOT NULL

    )''')

    con.execute('''CREATE TABLE environments (

        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        path TEXT NOT NULL,

        -- Attributes parsed from original file.
        version TEXT NOT NULL,
        revision TEXT NOT NULL

    )''')

    con.execute('''CREATE TABLE links (

        id INTEGER PRIMARY KEY,
        install_id INTEGER REFERENCES installs(id) NOT NULL,
        environment_id INTEGER REFERENCES environments(id) NOT NULL,
        created_at TIMESTAMP NOT NULL,
        user_specification TEXT NOT NULL

    )''')



def _migrate(con):
    with con:
        con.execute('''CREATE TABLE IF NOT EXISTS migrations (
            name TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL
        )''')
        cur = con.execute('SELECT name FROM migrations')
        existing = set(row[0] for row in cur)
    for f in _migrations:
        name = f.__name__.strip('_')
        if name not in existing:
            with con.begin():
                f(con)
                con.execute('INSERT INTO migrations VALUES (?, ?)', (name, datetime.datetime.utcnow()))



class _Connection(sqlite3.Connection):
    
    def __init__(self, *args, **kwargs):
        super(_Connection, self).__init__(*args, **kwargs)
        self.row_factory = sqlite3.Row

    def cursor(self):
        return super(_Connection, self).cursor(_Cursor)

    def begin(self):
        self.execute("BEGIN")
        return self


class _Cursor(sqlite3.Cursor):
    pass


class Index(object):

    def __init__(self, path):
        self.path = path
        _migrate(self.connect())

    def connect(self):
        return sqlite3.connect(self.path, factory=_Connection, isolation_level=None)

    def cursor(self):
        return self.connect().cursor()

