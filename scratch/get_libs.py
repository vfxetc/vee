import errno
import os
import shutil
from subprocess import check_output, call


CONTENTS = os.path.abspath('SitG.app/Contents')


def makedirs(x):
    try:
        os.makedirs(x)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


copied = set([

    # System tools.
    'python',

    # Build tools to ignore.
    'cmake',
    'git',
    'pkg-config',
    'texi2html',

])

to_copy = ['pyside']


while to_copy:

    name = to_copy.pop()
    if name in copied:
        continue
    copied.add(name)
    new_names = check_output(['brew', 'deps', name]).strip().split()
    to_copy.extend(new_names)

    print name

    old_pkg_home = os.path.realpath('/usr/local/opt/' + name)
    new_pkg_home = CONTENTS + '/opt/' + name

    # "makedepend" does not exist.
    if not os.path.exists(old_pkg_home):
        continue

    makedirs(new_pkg_home)
    call(['rsync', '-ax',

        '--include', 'LICENSE*',

        # Python
        '--include', '/bin/python2.7',
        '--exclude', '/bin/*',

        # (Py)Qt
        '--include', 'Qt.*',
        '--include', 'QtCore.*',
        '--include', 'QtGui.*',
        '--exclude', 'Qt*.*',
        '--exclude', '*phonon*',
        '--exclude', '/imports',
        '--exclude', '/mkspecs',
        '--exclude', '/phrasebooks',
        '--exclude', '/plugins',
        '--exclude', '/translations',

        # General
        '--exclude', '*.a',
        '--exclude', '*.app',
        '--exclude', '*.h',
        '--exclude', '.DS_Store',
        '--exclude', 'cmake',
        '--exclude', 'Headers',
        '--exclude', 'include',
        '--exclude', 'INSTALL_RECEIPT.json',
        '--exclude', 'pkgconfig',
        '--exclude', 'share',
        '--exclude', 'test',
        '--exclude', 'tests',

        old_pkg_home + '/', new_pkg_home + '/'
    ])

    # Fix any internal symlinks that were absolute.
    for dir_path, dir_names, file_names in os.walk(new_pkg_home):
        for file_name in file_names:
            link_name = os.path.abspath(os.path.join(dir_path, file_name))
            old_source = os.path.realpath(link_name)
            if link_name != old_source and not old_source.startswith(CONTENTS):
                new_source = os.path.join(
                    os.path.dirname(os.path.relpath(new_pkg_home, link_name)),
                    os.path.relpath(old_source, old_pkg_home),
                )
                os.unlink(link_name)
                os.symlink(new_source, link_name)

    # Symlink some parts together.
    # We could also do bin/lib/include/etc., but it feels clean enough to leave
    # everything in their own directories.
    for subdir in ('Frameworks', ):
        if not os.path.exists(os.path.join(new_pkg_home, subdir)):
            continue

        for x in os.listdir(os.path.join(new_pkg_home, subdir)):
            link_name = os.path.join(CONTENTS, subdir, x)
            link_source = os.path.relpath(os.path.join(new_pkg_home, subdir, x), os.path.dirname(link_name))
            if not os.path.exists(link_name):
                makedirs(os.path.dirname(link_name))
                os.symlink(link_source, link_name)




