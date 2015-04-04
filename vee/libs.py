import os
import re
import stat

from vee.subproc import call
from vee import log


def iter_unique(xs):
    seen = set()
    for x in xs:
        if x in seen:
            continue
        seen.add(x)
        yield x


def name_variants(name):

    res = [name]
    m = re.match(r'^(?:lib)?(.+?)(\.so|\.dylib)?(\..+)?$', name)
    if m:
        base, _, extpost = m.groups()
        res.append(base)
        for ext in '.dylib', '.so':
            if extpost:
                res.append('lib%s%s%s' % (base, ext, extpost))
            res.append('lib%s%s' % (base, ext))

    return list(iter_unique(res))


def get_dependencies(path):
    raw = call(['otool', '-L', path], stdout=True)
    lines = raw.strip().splitlines()

    id_ = lines[0][:-1]
    deps = []

    for line in lines[1:]:
        deps.append(re.sub(r'\s*\(.+?\)$', '', line.strip()))

    return id_, deps


# Assuming that VEE doesn't have a very long lifetime, this isn't the
# worst idea...
_symbol_cache = {}

def get_symbols(path):
    
    if path not in _symbol_cache:

        undefined = set()
        defined = set()

        raw = call(['nm', '-gP', path], stdout=True)
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            name, type_, _ = line.split(None, 2)
            if type_ in 'TDBC':
                defined.add(name)
            elif type_ == 'U':
                undefined.add(name)

        _symbol_cache[path] = frozenset(defined), frozenset(undefined)

    return _symbol_cache[path]


MACHO_TAGS = set((

    'feedface',
    'cefaefde',
    'feedfacf',
    'cffaedfe',

    'cafebabe', # For FAT files?
    'bebafeca',

))


def find_shared_libraries(path):

    for dir_path, dir_names, file_names in os.walk(path):

        allow_blank_ext = None

        for file_name in file_names:
            ext = os.path.splitext(file_name)[1]

            # Frameworks on OSX leave out extensions much of the time,
            # so we need to manually detech MachO's magic tag.
            if not ext:
                
                if allow_blank_ext is None:
                    allow_blank_ext = bool(re.search(r'\.framework(/|$)|/MacOS(/|$)', dir_path))
                if not allow_blank_ext:
                    continue

                path = os.path.join(dir_path, file_name)
                try:
                    tag = open(path, 'rb').read(4).encode('hex')
                except IOError:
                    continue
                if tag in MACHO_TAGS:
                    yield path

            # Obvious ones.
            if ext in ('.so', '.dylib'):
                yield os.path.join(dir_path, file_name)


def get_installed_shared_libraries(con, package_id, install_path, rescan=False):

    with con:

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


def relocate(root, con, spec=None, dry_run=False, target_cache=None):

    target_cache = {} if target_cache is None else target_cache

    auto = False
    include = []
    exclude = []

    if spec is None:
        spec = [None]
    if not isinstance(spec, (list, tuple)):
        spec = [x.strip() for x in spec.split(',')]

    for x in spec:
        if x in (None, '', 'AUTO'):
            auto = True
        elif x in ('SELF', ):
            include.append(root)
        elif x.startswith('/'):
            include.append(x)
        elif x.startswith('-/') or x.startswith('!/'):
            exclude.append(x[1:])
        else:
            raise ValueError('malformed relocate spec %r' % x)

    if not (auto or include):
        raise ValueError('no libraries to include')

    # Find everything in include.
    for path in include:
        for found in find_shared_libraries(path):
            log.debug('found %s' % found)
            for name in name_variants(os.path.basename(found)):
                target_cache.setdefault(name, []).append(found)

    for lib_path in find_shared_libraries(root):

        # Skip symlinks.
        lib_stat = os.lstat(lib_path)
        if stat.S_ISLNK(lib_stat.st_mode):
            continue

        _relocate_library(lib_path, con, auto, include, exclude, dry_run, target_cache)


def _relocate_library(lib_path, con, auto, include, exclude, dry_run, target_cache):

    log.info(lib_path)

    lib_id, lib_deps = get_dependencies(lib_path)

    cmd = ['install_name_tool']

    if lib_id != lib_path:
        print '    -id %s' % lib_id
        cmd.extend(('-id', lib_path))

    lib_def, lib_undef = get_symbols(lib_path)

    for dep_path in lib_deps:

        if dep_path == lib_id:
            log.warning('The ID is included?! %s' % lib_path)
            continue

        do_exclude = any(dep_path.startswith(x) for x in exclude)
        if not do_exclude and os.path.exists(dep_path):
            log.debug('skipping %s' % dep_path)
            continue

        dep_name = os.path.basename(dep_path)

        targets = []

        for variant in name_variants(dep_name):
            if variant in target_cache:
                targets.extend(target_cache[variant])
            if auto:
                cur = con.execute('SELECT path FROM shared_libraries WHERE name = ? ORDER BY created_at DESC', [variant])
                new_targets = target_cache.setdefault(variant, [])
                new_targets.extend([row[0] for row in cur])
                targets.extend(new_targets)
        
        seen_targets = set()
        for target in targets:
            if target in seen_targets:
                continue
            seen_targets.add(target)

            tar_def, tar_undef = get_symbols(target)

            pros = len(tar_def.intersection(lib_undef))
            cons = len(tar_def.intersection(lib_def)) + len(lib_undef.intersection(lib_def))
            log.debug('+%d -%d %s' % (pros, cons, target), verbosity=2)
            if pros > cons:
                break
        else:
            log.warning('Could not relocate %s' % dep_path)
            continue

        log.info('%s -> %s' % (dep_name, target), verbosity=1)

        cmd.extend(('-change', dep_path, target))

    if len(cmd) > 1 and not dry_run:

        cmd.append(lib_path)

        s = os.stat(lib_path)
        if not s.st_mode & stat.S_IWUSR:
            os.chmod(lib_path, s.st_mode | stat.S_IWUSR)
            call(cmd)
            os.chmod(lib_path, s.st_mode)
        else:
            call(cmd)

