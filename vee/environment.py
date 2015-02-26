import errno
import os
import re

from vee.utils import makedirs, style
import vee.vendor.virtualenv as virtualenv


IGNORE_DIRS = frozenset(('.git', '.svn'))
IGNORE_FILES = frozenset(('.DS_Store', ))


class Environment(object):

    def __init__(self, name, home):
        self.home = home
        if name.startswith('/'):
            self.path = name
            self.name = os.path.relpath(name, home.abspath('environments'))
        else:
            self.name = name
            self.path = home.abspath('environments', name)
        self._db_id = None


    def create_if_not_exists(self):
        python = os.path.join(self.path, 'bin', 'python')
        if not os.path.exists(python):
            makedirs(self.path)
            print style('Creating Python virtualenv', 'blue', bold=True), style(self.path, bold=True)
            virtualenv.create_environment(self.path, no_setuptools=True, no_pip=True)

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

    def link_directory(self, dir_to_link):
        
        self.create_if_not_exists()

        python = os.path.join(self.path, 'bin', 'python')

        # TODO: Be like Homebrew, and be smarter about what we link, and what
        # we copy.

        for old_dir_path, dir_names, file_names in os.walk(dir_to_link):
            
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
                rel_path = os.path.join(rel_dir_path, file_name)

                # If it starts with a Python shebang, rewrite it.
                with open(old_path, 'rb') as old_fh:
                    old_shebang = old_fh.readline()
                    m = re.match(r'#!(|\S+/)([^\s/]+)', old_shebang)
                    if m:
                        new_bin = os.path.join(self.path, 'bin', m.group(2))
                        if os.path.exists(new_bin):
                            new_shebang = '#!%s%s' % (new_bin, old_shebang[m.end(2):])
                            print 'Rewriting shebang of', rel_path
                            print style('from: %s' % old_shebang.strip(), faint=True)
                            print style('  to: %s' % new_shebang.strip(), faint=True)
                            with open(new_path, 'wb') as new_fh:
                                new_fh.write(new_shebang)
                                new_fh.writelines(old_fh)
                                continue

                # Symlink it into place.
                try:
                    os.symlink(old_path, new_path)
                except OSError as e:
                    # TODO: have a vee-link-history.txt in each environment
                    # so that we can quickly check what is already linked there.
                    if e.errno != errno.EEXIST:
                        raise

