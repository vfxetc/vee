import errno
import os

from vee.utils import makedirs



def envsplit(value):
    return value.split(':') if value else []

def envjoin(*values):
    return ':'.join(x for x in values if x)


IGNORE_DIRS = frozenset(('.git', '.svn'))
IGNORE_FILES = frozenset(('.DS_Store', ))


class Environment(object):

    def __init__(self, name, home):
        self.name = name
        self.home = home
        self.root = home.abspath('environments', name)

    def link_directory(self, dir_to_link):
        
        # TODO: Be like Homebrew, and be smarter about what we link, and what
        # we copy.

        root = self.root
        makedirs(root)

        for old_dir_path, dir_names, file_names in os.walk(dir_to_link):
            
            rel_dir_path = os.path.relpath(old_dir_path, dir_to_link)
            new_dir_path = os.path.abspath(os.path.join(root, rel_dir_path))

            # Ignore AND skip these directories.
            dir_names[:] = [x for x in dir_names if x not in IGNORE_DIRS]
            for dir_name in dir_names:
                makedirs(os.path.join(new_dir_path, dir_name))

            for file_name in file_names:
                if file_name in IGNORE_FILES:
                    continue
                try:
                    os.symlink(
                        os.path.join(old_dir_path, file_name),
                        os.path.join(new_dir_path, file_name),
                    )
                except OSError as e:
                    # TODO: have a vee-link-history.txt in each environment
                    # so that we can quickly check what is already linked there.
                    if e.errno != errno.EEXIST:
                        raise

    def get_environ(self):
        return {
            'PATH': envjoin(os.path.join(self.root, 'bin'), os.environ.get('PATH')),
            'PYTHONPATH': envjoin(os.path.join(self.root, 'lib/python2.7/site-packages'), os.environ.get('PYTHONPATH')),
        }

