import errno
import os
import re
import shutil
import sys

from vee._vendor import virtualenv

from vee.cli import style
from vee.utils import makedirs
from vee import log
from vee.database import DBObject, Column


IGNORE_DIRS = frozenset(('.git', '.svn'))
IGNORE_FILES = frozenset(('.DS_Store', ))

TOP_LEVEL_DIRS = frozenset(('bin', 'etc', 'include', 'lib', 'lib64', 'sbin', 'share', 'opt', 'var'))


class Environment(DBObject):

    __tablename__ = 'environments'

    name = Column()
    path = Column()

    def __init__(self, name, home):
        super(Environment, self).__init__()
        self.home = home
        if name.startswith('/'):
            self.path = name
            self.name = os.path.relpath(name, home._abs_path('environments'))
        else:
            self.name = name
            self.path = home._abs_path('environments', name)

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

    def resolve_existing(self):
        if self.id is not None:
            return self.id
        cur = self.home.db.cursor()
        row = cur.execute('SELECT * FROM environments WHERE path = ?', [self.path]).fetchone()
        if row:
            self.id = row['id']
            self.name = row['name']
            return self.id

    def persist_in_db(self):
        if self.id is None:
            self.resolve_existing()
        return super(Environment, self).persist_in_db()

    def rewrite_shebang_or_link(self, old_path, new_path):
        if not self.rewrite_shebang(old_path, new_path):
            self._assert_real_dir(os.path.dirname(new_path))
            try:
                os.symlink(old_path, new_path)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

    def rewrite_shebang(self, old_path, new_path):

        # If it starts with a Python shebang, rewrite it.
        with open(old_path, 'rb') as old_fh:
            old_shebang = old_fh.readline()
            m = re.match(r'#!(|\S+/)([^\s/]+)', old_shebang)
            if not m:
                return

            new_bin = os.path.join(self.path, 'bin', m.group(2))
            if not os.path.exists(new_bin):
                return

            new_shebang = '#!%s%s' % (new_bin, old_shebang[m.end(2):])
            log.info('Rewriting shebang of %s' % new_bin, verbosity=1)
            log.debug('New shebang: %s' % new_shebang.strip(), verbosity=1)

            self._assert_real_dir(os.path.dirname(new_path))
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

            return True

    def _assert_real_dir(self, path):

        if not path.startswith(self.path):
            raise ValueError("not in environment: %s" % path)

        paths = []
        while len(path) > len(self.path):
            paths.append(path)
            path = os.path.dirname(path)


        for path in reversed(paths):

            if not os.path.exists(path):
                os.makedirs(path)
                continue

            if not os.path.islink(path):
                continue

            # Create a directory, and populate it with symlinks to its contents.
            link_dst = os.path.abspath(os.readlink(path))
            os.unlink(path)
            os.makedirs(path)
            if os.path.isdir(link_dst):
                for name in os.listdir(link_dst):
                    os.symlink(os.path.join(link_dst, name), os.path.join(path, name))


    def link_directory(self, dir_to_link):
        
        src_root = os.path.abspath(dir_to_link)
        dst_root = self.path

        self.create_if_not_exists()

        for src_dir, dir_names, file_names in os.walk(src_root):
            
            _rel_dir = os.path.relpath(src_dir, src_root)
            dst_dir = os.path.abspath(os.path.join(dst_root, _rel_dir))

            # The top level should only have the standard directories,
            # and no files.
            if src_dir == src_root:
                dir_names[:] = [x for x in dir_names if x in TOP_LEVEL_DIRS]
                file_names = []

            # Determine if the currect dst directory is real, or there is a link
            # at some point.
            dst_dir_is_real = True
            dst_dir_is_mine = True
            dst_to_test = dst_dir
            while len(dst_to_test) > len(dst_root):
                is_link = os.path.exists and os.path.islink(dst_to_test)
                if is_link:
                    dst_dir_is_real = False
                    link_path = os.readlink(dst_to_test)
                    src_to_test = os.path.join(src_root, os.path.relpath(dst_to_test, dst_root))
                    if link_path != src_to_test:
                        dst_dir_is_mine = False
                        break
                dst_to_test = os.path.dirname(dst_to_test)

            if not dst_dir_is_mine:
                self._assert_real_dir(dst_dir)
                dst_dir_is_real = dst_dir_is_mine = True

            # Ignore and skip these directories, and remember to link the
            # others for later
            dir_names[:] = [x for x in dir_names if x not in IGNORE_DIRS]
            to_link = dir_names[:]

            # Check the files first, since they will determine if we need to
            # force this thing to be real.
            for name in file_names:
                if name in IGNORE_FILES:
                    continue

                src_path = os.path.join(src_dir, name)
                dst_path = os.path.join(dst_dir, name)

                if self.rewrite_shebang(src_path, dst_path):
                    dst_dir_is_real = True
                else:
                    to_link.append(name)

            # I guess we better link them...
            if dst_dir_is_real:
                for name in to_link:
                    src_path = os.path.join(src_dir, name)
                    dst_path = os.path.join(dst_dir, name)
                    try:
                        os.symlink(src_path, dst_path)
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            raise



