import os
import re
import stat

from vee.subproc import call
from vee import log


def get_dependencies(path):
    raw = call(['otool', '-L', path], stdout=True)
    lines = raw.strip().splitlines()

    id_ = lines[0][:-1]
    deps = []

    for line in lines[1:]:
        deps.append(re.sub(r'\s*\(.+?\)$', '', line.strip()))

    return id_, deps


MACHO_TAGS = set((
    'feedface',
    'cefaefde',
    'feedfacf',
    'cffaedfe',
))


def find_shared_libraries(path):

    for dir_path, dir_names, file_names in os.walk(path):
        for file_name in file_names:
            ext = os.path.splitext(file_name)[1]

            # Frameworks on OSX leave out extensions much of the time,
            # so we need to manually detech MachO's magic tag.
            if not ext and '.framework/' in dir_path:
                path = os.path.join(dir_path, file_name)
                tag = open(path, 'rb').read(4).encode('hex')
                if tag in MACHO_TAGS:
                    yield path

            # Obvious ones.
            if ext in ('.so', '.dylib'):
                yield os.path.join(dir_path, file_name)


def get_installed_shared_libraries(con, package_id, install_path, rescan=False):

    with con.begin():

        # Determine if we should scan.
        do_scan = rescan
        if not rescan:
            row = con.execute('SELECT scanned_for_libraries FROM packages WHERE id = ?', [package_id]).fetchone()
            do_scan = not row[0]

        # Return existing results if we should not scan.
        if not do_scan:
            cur = con.execute('SELECT path FROM shared_libraries WHERE package_id = ?', [package_id])
            return [row[0] for row in cur]

        # Blow out any existing results, and then scan.
        cur = con.execute('DELETE FROM shared_libraries WHERE package_id = ?', [package_id])

        res = []
        for lib_path in find_shared_libraries(install_path):
            res.append(lib_path)
            con.execute('''INSERT INTO shared_libraries (package_id, name, path) VALUES (?, ?, ?)''', [
                package_id, os.path.basename(lib_path), lib_path,
            ])
        
        con.execute('UPDATE packages SET scanned_for_libraries = 1 WHERE id = ?', [package_id])

        return res


def relocate(root, *args, **kwargs):

    for lib_path in find_shared_libraries(root):

        # Skip symlinks.
        lib_stat = os.lstat(lib_path)
        if stat.S_ISLNK(lib_stat.st_mode):
            continue

        relocate_library(lib_path, *args, **kwargs)

def relocate_library(lib_path, con, spec=None, dry_run=False, target_cache=None):

    spec = spec or 'AUTO'

    auto = False
    include = []
    exclude = []

    if spec is None:
        spec = ['AUTO']
    if not isinstance(spec, (list, tuple)):
        spec = [x.strip() for x in spec.split(',')]

    for x in spec:
        if x == 'AUTO':
            auto = True
        elif x.startswith('/'):
            include.append(x)
        elif x.startswith('-/'):
            exclude.append(x[1:])
        else:
            raise ValueError('malformed relocate spec %r' % x)

    if not auto or include:
        raise ValueError('no libraries to include')

    target_cache = {} if target_cache is None else target_cache

    # Find everything in include.
    for path in include:
        for found in find_shared_libraries(path):
            target_cache.setdefault(os.path.basename(found), []).append(found)

    print lib_path

    lib_id, lib_deps = get_dependencies(lib_path)

    cmd = ['install_name_tool']

    if lib_id != lib_path:
        print '    -id %s' % lib_id
        cmd.extend(('-id', lib_path))

    for dep_path in lib_deps:

        do_exclude = any(dep_path.startswith(x) for x in exclude)
        if not do_exclude and os.path.exists(dep_path):
            print '    # skip %s' % dep_path
            continue

        dep_name = os.path.basename(dep_path)

        if dep_name not in target_cache:
            if auto:
                cur = con.execute('SELECT path FROM shared_libraries WHERE name = ? ORDER BY created_at DESC', [dep_name])
                target_cache[dep_name] = [row[0] for row in cur]
            else:
                raise RuntimeError('could not find lib for %s' % dep_name)

        targets = target_cache[dep_name]

        if not targets:
            log.warning('Could not find target for %s' % dep_path)
            continue

        print '    -change %s \\\n            %s' % (dep_path, targets[0])
        cmd.extend(('-change', dep_path, targets[0]))

    if len(cmd) > 1 and not dry_run:

        cmd.append(lib_path)

        s = os.stat(lib_path)
        if not s.st_mode & stat.S_IWUSR:
            os.chmod(lib_path, s.st_mode | stat.S_IWUSR)
            call(cmd)
            os.chmod(lib_path, s.st_mode)
        else:
            call(cmd)

