import errno
import os
import re
import shutil
import sys

from vee._vendor import virtualenv

from vee.cli import style
from vee.utils import makedirs
from vee import log


IGNORE_DIRS = frozenset(('.git', '.svn'))
IGNORE_FILES = frozenset(('.DS_Store', ))

TOP_LEVEL_DIRS = frozenset(('bin', 'etc', 'include', 'lib', 'lib64', 'sbin', 'share', 'opt', 'var'))


class Environment(object):

    def __init__(self, name, home):
        self.home = home
        if name.startswith('/'):
            self.path = name
            self.name = os.path.relpath(name, home._abs_path('environments'))
        else:
            self.name = name
            self.path = home._abs_path('environments', name)
        self._db_id = None


    def create_if_not_exists(self):

        python = os.path.join(self.path, 'bin', 'python')
        if not os.path.exists(python):
            makedirs(self.path)
            print style('Creating Python virtualenv', 'blue', bold=True), style(self.path, bold=True)
            virtualenv.create_environment(self.path, no_setuptools=True, no_pip=True)

        if not os.path.exists(python + '-config'):
            names = (
                'python%d.%d-config' % sys.version_info[:2],
                'python%d-config' % sys.version_info[0],
                'python-config',
            )
            prefix = getattr(sys, 'real_prefix', sys.prefix)
            for name in names:
                old_path = os.path.join(prefix, 'bin', name)
                if os.path.exists(old_path):
                    for name in names:
                        new_path = os.path.join(self.path, 'bin', name)
                        self.rewrite_shebang_or_link(old_path, new_path)
                    break
            else:
                log.warning('Could not find python-config')

    def db_id(self):
        if self._db_id is None:
            cur = self.home.db.cursor()
            row = cur.execute('SELECT * FROM environments WHERE path = ?', [self.path]).fetchone()
            if row:
                self._db_id = row['id']
            else:
                cur.execute('INSERT INTO environments (name, path) VALUES (?, ?)', [
                    self.name, self.path,
                ])
                self._db_id = cur.lastrowid
        return self._db_id

    def rewrite_shebang_or_link(self, old_path, new_path):

        # If it starts with a Python shebang, rewrite it.
        with open(old_path, 'rb') as old_fh:
            old_shebang = old_fh.readline()
            m = re.match(r'#!(|\S+/)([^\s/]+)', old_shebang)
            if m:
                new_bin = os.path.join(self.path, 'bin', m.group(2))
                if os.path.exists(new_bin):
                    new_shebang = '#!%s%s' % (new_bin, old_shebang[m.end(2):])
                    log.info('Rewriting shebang of %s' % new_bin, verbosity=1)
                    log.debug('New shebang: %s' % new_shebang.strip(), verbosity=1)
                    with open(new_path, 'wb') as new_fh:
                        new_fh.write(new_shebang)
                        new_fh.writelines(old_fh)
                    try:
                        shutil.copystat(old_path, new_path)
                    except OSError as e:
                        # These often come up when you are not the owner
                        # of the file.
                        if e.errno != errno.EPERM:
                            raise
                    return

        # Symlink it into place.
        if os.path.exists(new_path):
            os.unlink(new_path)
        try:
            os.symlink(old_path, new_path)
        except OSError as e:
            # TODO: have a vee-link-history.txt in each environment
            # so that we can quickly check what is already linked there.
            if e.errno != errno.EEXIST:
                raise

    def link_directory(self, dir_to_link):
        
        dir_to_link = os.path.abspath(dir_to_link)

        self.create_if_not_exists()

        python = os.path.join(self.path, 'bin', 'python')

        # TODO: Be like Homebrew, and be smarter about what we link, and what
        # we copy.

        top_level = True

        for old_dir_path, dir_names, file_names in os.walk(dir_to_link):
            
            # The top level should only have the standard directories,
            # and no files.
            if top_level:
                file_names = []
                dir_names[:] = [x for x in dir_names if x in TOP_LEVEL_DIRS]
                top_level = False

            rel_dir_path = os.path.relpath(old_dir_path, dir_to_link)
            new_dir_path = os.path.abspath(os.path.join(self.path, rel_dir_path))

            # Ignore AND skip these directories.
            dir_names[:] = [x for x in dir_names if x not in IGNORE_DIRS]
            for dir_name in dir_names:
                makedirs(os.path.join(new_dir_path, dir_name))

            for file_name in file_names:
                if file_name in IGNORE_FILES:
                    continue

                old_path = os.path.join(old_dir_path, file_name)
                new_path = os.path.join(new_dir_path, file_name)
                self.rewrite_shebang_or_link(old_path, new_path)

