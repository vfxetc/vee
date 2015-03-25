import contextlib
import datetime
import os
import sqlite3
import shutil

from vee.utils import makedirs
from vee import log


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

    con.execute('''CREATE TABLE development_packages (

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


@_migrations.append
def _rename_dev_packages(con):

    existing = set(row['name'] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'"))
    if 'dev_packages' in existing:
        con.execute('''ALTER TABLE dev_packages RENAME TO development_packages''')


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
        query = 'INSERT %s INTO %s (%s) VALUES (%s)' % (
            'OR ' + on_conflict if on_conflict else '',
            escape_identifier(table),
            ','.join(escape_identifier(k) for k, v in pairs),
            ','.join('?' for _ in pairs),

        )
        params = [v for k, v in pairs]
        log.debug('%s %r' % (query, params))
        self.execute(query, params)
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




class Column(object):

    def __init__(self, name=None):
        self.name = name
        self._fget = self._fset = self._fdel = None
        self._persist = None

    def copy(self):
        copy = Column(self.name)
        copy._fget = self._fget
        copy._persist = self._persist
        return copy

    def getter(self, func):
        self._fget = func
        return self

    def persist(self, func):
        self._persist = func
        return self

    def __get__(self, obj, cls):
        if self._fget:
            return self._fget(obj)
        try:
            return obj.__dict__[self.name]
        except KeyError:
            raise AttributeError(self.name)

    def __set__(self, obj, value):
        obj.__dict__[self.name] = value
        obj.is_dirty = True

    def __delete__(self, obj):
        raise RuntimeError("cannot delete DB columns")



class DBMetaclass(type):

    def __new__(cls, name, bases, attrs):

        columns = {}

        table_name = attrs.get('__tablename__')
        for base in bases:
            table_name = table_name or getattr(base, '__tablename__', None)
            for col in getattr(base, '__columns__', []):
                columns[col.name] = col

        for k, v in attrs.iteritems():
            if isinstance(v, property):
                col = columns.get(k)
                if col:
                    col = col.copy()
                    col._fget = v.fget
                    if v.fset or v.fdel:
                        raise ValueError('cannot wrap properties with setters')
                    attrs[k] = col
                    v = col

            if isinstance(v, Column):
                v.name = v.name or k
                columns[v.name] = v

        attrs['__columns__'] = columns.values()

        return super(DBMetaclass, cls).__new__(cls, name, bases, attrs)


class DBObject(object):

    __metaclass__ = DBMetaclass

    def __init__(self, *args, **kwargs):
        self.id = None
        self.is_dirty = True

    def _cursor(self):
        return self.home.db.cursor()

    def persist_in_db(self, cursor=None, force=False):

        if not self.is_dirty and not force:
            return self.id

        data = {}
        for col in self.__columns__:
            try:
                if col._persist:
                    data[col.name] = col._persist(self)
                elif col._fget:
                    data[col.name] = col._fget(self)
                else:
                    data[col.name] = self.__dict__[col.name]
            except KeyError:
                pass

        cursor = cursor or self._cursor()
        if self.id:
            cursor.update(self.__tablename__, data, {'id': self.id})
        else:
            self.id = cursor.insert(self.__tablename__, data)
            log.debug('%s added to %s with ID %d' % (self.__class__.__name__, self.__tablename__, self.id))
        self.is_dirty = False

        return self.id





