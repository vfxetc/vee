import contextlib
import datetime
import sqlite3


_migrations = []


@_migrations.append
def _create_initial_tables(con):

    con.execute('''CREATE TABLE packages (

        id INTEGER PRIMARY KEY,
        created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),

        -- Requirement.to_json()
        abstract_requirement TEXT NOT NULL,
        concrete_requirement TEXT NOT NULL,

        type TEXT NOT NULL,
        url TEXT NOT NULL,

        name TEXT,
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
        created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
        modified_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),

        name TEXT NOT NULL,
        path TEXT NOT NULL,

        -- Attributes parsed from original file.
        version TEXT,
        revision TEXT

    )''')

    con.execute('''CREATE TABLE links (

        id INTEGER PRIMARY KEY,
        created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),

        environment_id INTEGER REFERENCES environments(id) NOT NULL,
        package_id INTEGER REFERENCES packages(id) NOT NULL,

        abstract_requirement TEXT NOT NULL

    )''')

    con.execute('''CREATE TRIGGER on_insert_links

        AFTER INSERT ON links BEGIN
            UPDATE environments SET modified_at = datetime('now') WHERE id = NEW.environment_id;
        END

    ''')

    con.execute('''CREATE TABLE config (

        id INTEGER PRIMARY KEY,
        created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),

        name TEXT UNIQUE NOT NULL,
        value TEXT NOT NULL

    )''')



def _migrate(con):
    with con:
        con.execute('''CREATE TABLE IF NOT EXISTS migrations (
            name TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
        )''')
        cur = con.execute('SELECT name FROM migrations')
        existing = set(row[0] for row in cur)
    for f in _migrations:
        name = f.__name__.strip('_')
        if name not in existing:
            with con.begin():
                f(con)
                con.execute('INSERT INTO migrations (name) VALUES (?)', [name])



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


class Database(object):

    def __init__(self, path):
        self.path = path
        _migrate(self.connect())

    def connect(self):
        return sqlite3.connect(self.path, factory=_Connection, isolation_level=None)

    def cursor(self):
        return self.connect().cursor()

    def execute(self, *args):
        return self.connect().execute(*args)


