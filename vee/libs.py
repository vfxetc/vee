import os
import re

from vee.subproc import call


def get_dependencies(path):
    res = call(['otool', '-L', path], stdout=True)
    for line in res.strip().splitlines()[1:]:
        dep_path = re.sub(r'\s*\(.+?\)$', '', line.strip())
        yield dep_path


MACHO_TAGS = set((
    'feedface',
    'cefaefde',
    'feedfacf',
    'cffaedfe',
))

def find_libraries(path):
    for dir_path, dir_names, file_names in os.walk(path):
        for file_name in file_names:
            ext = os.path.splitext(file_name)[1]

            # Frameworks on OSX leave out extensions much of the time.
            if not ext and '.framework/' in dir_path:
                path = os.path.join(dir_path, file_name)
                tag = open(path, 'rb').read(4).encode('hex')
                if tag in MACHO_TAGS:
                    yield path

            # Obvious ones.
            if ext in ('.so', '.dylib'):
                yield os.path.join(dir_path, file_name)


def find_package_libraries(home, install_path, package_id, force=False):

    con = home.db.connect()
    with con.begin():

        # Determine if we should scan.
        do_scan = force
        if not force:
            row = con.execute('SELECT scanned_for_libraries FROM packages WHERE id = ?', [package_id]).fetchone()
            do_scan = not row[0]

        # Return existing results if we should not scan.
        if not do_scan:
            cur = con.execute('SELECT rel_path FROM installed_libraries WHERE package_id = ?', [package_id])
            return [row[0] for row in cur]

        # Blow out any existing results, and then scan.
        cur = con.execute('DELETE FROM installed_libraries WHERE package_id = ?', [package_id])

        res = []
        for lib_path in find_libraries(install_path):
            rel_path = os.path.relpath(lib_path, install_path)
            res.append(rel_path)
            con.execute('''INSERT INTO installed_libraries (package_id, name, rel_path) VALUES (?, ?, ?)''', [
                package_id, os.path.basename(lib_path), rel_path
            ])
        
        con.execute('UPDATE packages SET scanned_for_libraries = 1 WHERE id = ?', [package_id])

        return res
