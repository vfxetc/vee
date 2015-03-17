import contextlib
import datetime
import os
import sqlite3
import shutil

from vee.utils import makedirs


_migrations = []


@_migrations.append
def _create_initial_tables(con):

    con.execute('''CREATE TABLE repositories (

        id INTEGER PRIMARY KEY,
        created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
        fetched_at TIMESTAMP,

        name TEXT UNIQUE NOT NULL,
        path TEXT,
        remote TEXT NOT NULL DEFAULT 'origin',
        branch TEXT NOT NULL DEFAULT 'master',

        is_default INTEGER NOT NULL DEFAULT 0

    )''')

    con.execute('''CREATE TRIGGER insert_default_repository

        AFTER INSERT ON repositories
        WHEN NEW.is_default
        BEGIN
            UPDATE repositories SET is_default = 0 WHERE id != NEW.id;
        END

    ''')

    con.execute('''CREATE TRIGGER update_default_repository

        AFTER UPDATE OF is_default ON repositories
        WHEN NEW.is_default != 0
        BEGIN
            UPDATE repositories SET is_default = 0 WHERE id != NEW.id;
        END

    ''')

    con.execute('''CREATE TABLE packages (

        id INTEGER PRIMARY KEY,
        created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),

        -- Requirement.to_json()
        abstract_requirement TEXT NOT NULL,
        concrete_requirement TEXT NOT NULL,

        url TEXT NOT NULL,
        name TEXT,
        revision TEXT,
        etag TEXT,

        package_type TEXT NOT NULL,
        build_type TEXT NOT NULL,

        -- Names, either from the user or discovered.
        package_name TEXT,
        build_name TEXT,
        install_name TEXT,

        -- Paths for direct lookup.
        package_path TEXT,
        build_path TEXT,
        install_path TEXT,

        scanned_for_libraries INTEGER NOT NULL DEFAULT 0

    )''')

    con.execute('''CREATE TABLE environments (

        id INTEGER PRIMARY KEY,
        created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
        modified_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),

        repository_id INTEGER REFERENCES repositories(id),
        repository_commit TEXT,

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

    con.execute('''CREATE TABLE dev_packages (

        id INTEGER PRIMARY KEY,
        created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),

        name TEXT NOT NULL,
        path TEXT NOT NULL,

        environ TEXT NOT NULL DEFAULT "{}"

    )''')

    con.execute('''CREATE TABLE config (

        id INTEGER PRIMARY KEY,
        created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),

        name TEXT UNIQUE NOT NULL,
        value TEXT NOT NULL

    )''')


@_migrations.append
def _create_repos_path_column(con):
    existing = set(row['name'] for row in con.execute('PRAGMA table_info(repositories)'))
    if 'path' not in existing:
        con.execute('''ALTER TABLE repositories ADD COLUMN path TEXT''')

@_migrations.append
def _create_packages_etag_column(con):
    existing = set(row['name'] for row in con.execute('PRAGMA table_info(packages)'))
    if 'etag' not in existing:
        con.execute('''ALTER TABLE packages ADD COLUMN etag TEXT''')

@_migrations.append
def _created_shared_libraries(con):

    existing = set(row['name'] for row in con.execute('PRAGMA table_info(packages)'))
    if 'scanned_for_libraries' not in existing:
        con.execute('''ALTER TABLE packages ADD COLUMN scanned_for_libraries INTEGER NOT NULL DEFAULT 0''')

    con.execute('''CREATE TABLE shared_libraries (

        id INTEGER PRIMARY KEY,
        created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),

        package_id INTEGER REFERENCES packages(id) NOT NULL,
        name TEXT NOT NULL, -- Mainly for searching.
        path TEXT NOT NULL

    )''')


class _Connection(sqlite3.Connection):
    
    def __init__(self, *args, **kwargs):
        super(_Connection, self).__init__(*args, **kwargs)
        self.row_factory = sqlite3.Row

        # We wish we could use unicode everywhere, but there are too many
        # unknown codepaths for us to evaluate its safety. Python 3 would
        # definitely help us here...
        self.text_factory = str

    def cursor(self):
        return super(_Connection, self).cursor(_Cursor)

    def begin(self):
        self.execute("BEGIN")
        return self


def escape_identifier(x):
    return '"%s"' % x.replace('"', '""')


class _Cursor(sqlite3.Cursor):
    
    def insert(self, table, data, on_conflict=None):
        pairs = sorted(data.iteritems())
        self.execute('INSERT %s INTO %s (%s) VALUES (%s)' % (
            'OR ' + on_conflict if on_conflict else '',
            escape_identifier(table),
            ','.join(escape_identifier(k) for k, v in pairs),
            ','.join('?' for _ in pairs),

        ), [v for k, v in pairs])
        return self.lastrowid

    def update(self, table, data, where=None):
        columns, params = zip(*sorted(data.iteritems()))
        if where:
            where = sorted(where.iteritems())
            params = list(params)
            params.extend(v for k, v in where)
            where = 'WHERE %s' % ' AND '.join('%s = ?' % escape_identifier(k) for k, v in where)
        self.execute('UPDATE %s SET %s %s' % (
            escape_identifier(table),
            ', '.join('%s = ?' % escape_identifier(c) for c in columns),
            where or '',
        ), params)
        return self


class Database(object):

    def __init__(self, path):
        self.path = path
        self._migrate()

    def _migrate(self):
        did_backup = False
        con = self.connect()
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
                if not did_backup:
                    self._backup()
                did_backup = True
                with con.begin():
                    f(con)
                    con.execute('INSERT INTO migrations (name) VALUES (?)', [name])

    def _backup(self):
        backup_dir = os.path.join(os.path.dirname(self.path), 'backups')
        backup_path = os.path.join(backup_dir, os.path.basename(self.path) + '.' + datetime.datetime.utcnow().isoformat('T'))
        makedirs(backup_dir)
        shutil.copyfile(self.path, backup_path)

    @property
    def exists(self):
        return os.path.exists(self.path)

    def connect(self):
        makedirs(os.path.dirname(self.path))
        return sqlite3.connect(self.path, factory=_Connection, isolation_level=None)

    def cursor(self):
        return self.connect().cursor()

    def execute(self, *args):
        return self.connect().execute(*args)

    def insert(self, *args, **kwargs):
        return self.cursor().insert(*args, **kwargs)

    def update(self, *args, **kwargs):
        return self.cursor().update(*args, **kwargs)



