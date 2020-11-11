import datetime
import os
import sqlite3
import shutil
import re

import six

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

        url TEXT NOT NULL,
        name TEXT,
        revision TEXT,
        etag TEXT,

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
        package_id INTEGER REFERENCES packages(id) NOT NULL

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
    if 'path' not in con.columns('repositories'):
        con.execute('''ALTER TABLE repositories ADD COLUMN path TEXT''')

@_migrations.append
def _create_packages_etag_column(con):
    if 'etag' not in con.columns('packages'):
        con.execute('''ALTER TABLE packages ADD COLUMN etag TEXT''')

@_migrations.append
def _created_shared_libraries(con):

    if 'scanned_for_libraries' not in con.columns('packages'):
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
    if 'dev_packages' in con.tables():
        con.execute('''ALTER TABLE dev_packages RENAME TO development_packages''')

@_migrations.append
def _drop_type_columns(con):
    if 'package_type' in con.columns('packages'):
        con.drop_column('packages', 'package_type')
    if 'build_type' in con.columns('packages'):
        con.drop_column('packages', 'build_type')

@_migrations.append
def _create_dependency_table(con):
    con.execute('''CREATE TABLE package_dependencies (

        id INTEGER PRIMARY KEY,
        created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),

        depender_id INTEGER REFERENCES packages(id) NOT NULL,
        dependee_id INTEGER REFERENCES packages(id) NOT NULL

    )''')

@_migrations.append
def _drop_dev_packages(con):
    if 'development_packages' in con.tables():
        con.execute('''DROP TABLE development_packages''')



class _Row(sqlite3.Row):

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key):
        try:
            return super(_Row, self).__getitem__(key)
        except IndexError:
            if isinstance(key, str):
                raise KeyError(key)
            else:
                raise

    def __contains__(self, key):
        try:
            self[key]
            return True
        except (IndexError, KeyError):
            return False


class _Connection(sqlite3.Connection):
    
    def __init__(self, *args, **kwargs):
        super(_Connection, self).__init__(*args, **kwargs)
        self.row_factory = _Row

        # We wish we could use unicode everywhere, but there are too many
        # unknown codepaths for us to evaluate its safety. Python 3 would
        # definitely help us here...
        self.text_factory = str

        self.isolation_level = None
        self._context_depth = 0

    def __enter__(self):
        if not self._context_depth:
            self.execute('BEGIN')
        else:
            self.execute('SAVEPOINT pycontext%d' % self._context_depth)
        self._context_depth += 1
        return self

    def __exit__(self, type_, value, tb):
        self._context_depth -= 1
        if type_:
            if not self._context_depth:
                self.execute('ROLLBACK')
            else:
                self.execute('ROLLBACK TO pycontext%d' % self._context_depth)
        else:
            if not self._context_depth:
                self.execute('COMMIT')
            else:
                self.execute('RELEASE pycontext%d' % self._context_depth)

    def cursor(self):
        return super(_Connection, self).cursor(_Cursor)

    def insert(self, *args, **kwargs):
        return self.cursor().insert(*args, **kwargs)
        
    def update(self, *args, **kwargs):
        return self.cursor().update(*args, **kwargs)

    def tables(self):
        return [row['name'] for row in self.execute("SELECT name FROM sqlite_master WHERE type='table'")]

    def schema(self, table_name):
        return self.execute('SELECT sql FROM sqlite_master WHERE name = ?', [table_name]).fetchone()['sql']

    def columns(self, table_name):
        return [row['name'] for row in self.execute('PRAGMA table_info(%s)' % table_name)]

    def drop_column(self, table_name, column_name):

        old_columns = self.columns(table_name)
        new_columns = [x for x in old_columns if x != column_name]
        if new_columns == old_columns:
            raise ValueError(column_name)

        old_schema = self.schema(table_name)
        new_schema = re.sub(r'\)\s*$', ',', old_schema)
        new_schema = re.sub('%s[^,]+,' % column_name, '', new_schema)
        new_schema = re.sub(r',$', ')', new_schema)
        if new_schema == old_schema:
            raise ValueError('no change in schema: %s' % new_schema)

        self.execute('ALTER TABLE %s RENAME TO old_%s' % (table_name, table_name))
        self.execute(new_schema)
        self.execute('INSERT INTO %s (%s) SELECT %s FROM old_%s' % (
            table_name, ','.join(new_columns), ','.join(new_columns), table_name
        ))
        self.execute('DROP TABLE old_%s' % table_name)






def escape_identifier(x):
    return '"%s"' % x.replace('"', '""')


class _Cursor(sqlite3.Cursor):
    
    def insert(self, table, data, on_conflict=None):
        pairs = sorted(data.items())
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
        columns, params = zip(*sorted(data.items()))
        if where:
            where = sorted(where.items())
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
        if self.exists:
            self._migrate()

    def _migrate(self, con=None):
        did_backup = False
        con = con or self.connect()
        with con:

            # We try to select without creating the table, so that we don't
            # force the database to lock every time (which will fail if
            # something else has an exclusive lock).
            try:
                cur = con.execute('SELECT name FROM migrations')

            except sqlite3.OperationalError as e:
                if e.args[0] != 'no such table: migrations':
                    raise

                con.execute('''CREATE TABLE IF NOT EXISTS migrations (
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
                )''')
                existing = set()

            else:
                existing = set(row[0] for row in cur)

        for f in _migrations:
            name = f.__name__.strip('_')
            if name not in existing:
                if not did_backup:
                    self._backup()
                did_backup = True
                with con:
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

    def create(self):
        if self.exists:
            raise ValueError('database already exists')
        con = self.connect(create=True)
        self._migrate(con)

    def connect(self, create=False):
        if not create and not self.exists:
            raise ValueError('database does not exist; run `vee init`')
        con = sqlite3.connect(self.path, factory=_Connection)
        con.execute('PRAGMA foreign_keys = ON')
        return con

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
        self._getter = self._setter = self._deleter = None
        self._persist = self._restore = None

    def copy(self):
        copy = Column(self.name)
        copy._getter  = self._getter
        copy._persist = self._persist
        copy._restore = self._restore
        return copy

    def getter(self, func):
        self._getter = func
        return self

    def persist(self, func):
        self._persist = func
        return self

    def restore(self, func):
        self._restore = func
        return self

    def __get__(self, obj, cls):
        if self._getter:
            return self._getter(obj)
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

        table_name = attrs.get('__tablename__')

        # Collect existing columns from bases.
        columns = {}
        for base in reversed(bases):
            table_name = table_name or getattr(base, '__tablename__', None)
            for col in getattr(base, '__columns__', []):
                columns[col.name] = col.copy()

        # Collect new columns.
        for k, v in attrs.items():

            # If this is now a property, but it was once a column, upgrade it
            # to a column.
            if isinstance(v, property):
                col = columns.get(k)
                if col:
                    col._getter = v.fget
                    if v.fset or v.fdel:
                        raise ValueError('cannot wrap properties with setters or deleters')
                    attrs[k] = col
                    v = col

            if isinstance(v, Column):
                v.name = v.name or k
                columns[v.name] = v

        attrs['__columns__'] = [v for _, v in sorted(columns.items())]

        return super(DBMetaclass, cls).__new__(cls, name, bases, attrs)


@six.add_metaclass(DBMetaclass)
class DBObject(object):

    def __init__(self, *args, **kwargs):
        self.id = None
        self.is_dirty = True

    def _connect(self):
        return self.home.db.connect()

    def id_or_persist(self, *args, **kwargs):
        return self.id or self.persist_in_db(*args, **kwargs)

    def persist_in_db(self, con=None, force=False):

        if not self.is_dirty and not force:
            return self.id

        data = {}
        for col in self.__columns__:
            try:
                if col._persist:
                    data[col.name] = col._persist(self)
                elif col._getter:
                    data[col.name] = col._getter(self)
                else:
                    data[col.name] = self.__dict__[col.name]
            except KeyError:
                pass

        con = con or self._connect()
        if self.id:
            con.update(self.__tablename__, data, {'id': self.id})
        else:
            self.id = con.insert(self.__tablename__, data)
            log.debug('%s added to %s with ID %d' % (self.__class__.__name__, self.__tablename__, self.id))
        self.is_dirty = False

        return self.id

    def restore_from_row(self, row, ignore=None):
        
        try:
            if self.id and self.id != row['id']:
                log.warning('Restoring from a mismatched ID; %s %d != %d' % (self.__tablename__, self.id, row['id']))
            self.id = row['id']
        except KeyError:
            pass
        
        for col in self.__columns__:

            try:
                val = row[col.name]
            except KeyError:
                continue

            if ignore and col.name in ignore:
                continue

            if col._restore:
                col._restore(self, val)
            else:
                self.__dict__[col.name] = val






