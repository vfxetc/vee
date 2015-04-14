import os
import re
import stat
import itertools
import sys

from vee.subproc import call
from vee import log


def iter_unique(xs):
    seen = set()
    for x in xs:
        if x in seen:
            continue
        seen.add(x)
        yield x


def name_variants(name, version_only=False):

    res = [name]
    m = re.match(r'^(lib)?(.+?)([-\.\d]+)?(\.so|\.dylib)?(\..+)?$', name)
    if m:
        m_lib, base, m_version, m_ext, m_post = m.groups()
        version_parts = re.split(r'([-\.])', m_version) if m_version else []

        if version_only:
            posts = (m_post or '', )
            exts  = (m_ext  or '', )
            libs  = (m_lib  or '', )
        else:
            posts = m_post or '', ''
            exts  = m_ext  or '', '.dylib', '.so', ''
            libs  = m_lib  or '', '', 'lib'

        versions = []
        for version_i in xrange(-1, len(version_parts) + 1, 2):
            version = ''.join(version_parts[:version_i]) if version_i > 0 else ''
            versions.insert(0, version)

        for post, lib, version, ext in itertools.product(posts, libs, versions, exts):
            new_name = '%s%s%s%s%s' % (lib, base, version, ext, post)
            res.append(new_name)

    return list(iter_unique(res))


def get_dependencies(path):

    ids = _parse_otool(call(['otool', '-D', path], stdout=True))
    id_ = ids[0] if ids else None

    deps = _parse_otool(call(['otool', '-L', path], stdout=True))

    # Trim off the ID.
    if deps and id_ and deps[0] == id_:
        deps = deps[1:]

    return id_, deps


def _parse_otool(raw):
    lines = raw.strip().splitlines()
    deps = []
    for line in lines[1:]:
        deps.append(re.sub(r'\s*\(.+?\)$', '', line.strip()))
    return deps


# Assuming that VEE doesn't have a very long lifetime, this isn't the
# worst idea...
_symbol_cache = {}
IGNORE_SYMBOLS = set(('_main', ))

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

            # Some symbols can safely be ignored. E.g. "_main", which we
            # sometimes see left over in some shared libs.
            if name in IGNORE_SYMBOLS:
                continue

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

            path = os.path.join(dir_path, file_name)
            if os.path.islink(path):
                continue

            ext = os.path.splitext(file_name)[1]

            # Frameworks on OSX leave out extensions much of the time, and
            # executable files in general won't have them so we need to manually
            # detect MachO's magic tag.
            if not ext:
                
                if allow_blank_ext is None:
                    allow_blank_ext = bool(re.search(r'(^|/)([^/]+\.framework|MacOS|bin|scripts)($/|)', dir_path))
                if not allow_blank_ext:
                    continue

                try:
                    tag = open(path, 'rb').read(4).encode('hex')
                except IOError:
                    continue
                if tag in MACHO_TAGS:
                    yield path

            # Obvious ones.
            if ext in ('.so', '.dylib'):
                yield path


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
            log.debug('Found shared library %s' % lib_path)
            res.append(lib_path)
            con.execute('''INSERT INTO shared_libraries (package_id, name, path) VALUES (?, ?, ?)''', [
                package_id, os.path.basename(lib_path), lib_path,
            ])
        
        con.execute('UPDATE packages SET scanned_for_libraries = 1 WHERE id = ?', [package_id])

        return res


def _parse_spec(spec, root):

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
            continue

        if x[0] in '!-':
            spec_set = exclude
            x = x[1:]
        else:
            spec_set = include

        if x == 'SELF':
            spec_set.append(root)
        elif x == 'HOMEBREW':
            spec_set.extend((
                '/usr/local/lib',
                '/usr/local/opt',
                '/usr/local/Cellar',
                '/usr/local/vee/packages/homebrew', # TODO: These should use current home.
                '/usr/local/vee/packages/linuxbrew',
            ))
        elif x.startswith('/'):
            spec_set.append(x)
        else:
            raise ValueError('malformed relocate spec %r' % x)

    return auto, include, exclude


def relocate(root, con, spec=None, dry_run=False, target_cache=None):

    target_cache = {} if target_cache is None else target_cache

    auto, include, exclude = _parse_spec(spec, root)

    if not (auto or include):
        raise ValueError('no libraries to include')

    if sys.platform == 'darwin':

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

            log.info(lib_path)
            with log.indent():
                _relocate_library(lib_path, con, auto, include, exclude, dry_run, target_cache)

    relocate_pkgconfig(root)


def relocate_pkgconfig(root):

    # Do trivial rewrites of pkgconfig files.
    pkg_config = os.path.join(root, 'lib', 'pkgconfig')
    if os.path.exists(pkg_config):
        for name in os.listdir(pkg_config):
            if not name.endswith('.pc'):
                continue
            path = os.path.join(pkg_config, name)
            log.info(path)
            lines = list(open(path))
            for i, line in enumerate(lines):
                if re.match(r'^prefix=([^\$]+)\s*$', line):
                    lines[i] = 'prefix=%s\n' % root
                    break
            else:
                with log.indent():
                    log.warning('No obvious prefix to replace')
                continue
            # As silly as this seems, *.pc files we have seen have their
            # write flag removed, but we still own them (since we just installed
            # them). Quickest way to fix: delete them.
            if not os.access(path, os.W_OK):
                os.unlink(path)
            with open(path, 'w') as fh:
                fh.writelines(lines)


def _relocate_library(lib_path, con, auto, include, exclude, dry_run, target_cache):


    lib_id, lib_deps = get_dependencies(lib_path)

    id_versions = set(name_variants(os.path.basename(lib_id), version_only=True)) if lib_id else set()
    lib_versions = set(name_variants(os.path.basename(lib_path), version_only=True))

    cmd = ['install_name_tool']

    if lib_id != lib_path:
        log.info('id %s' % (lib_path), verbosity=1)
        cmd.extend(('-id', lib_path))

    lib_def, lib_undef = get_symbols(lib_path)

    for dep_i, dep_path in enumerate(lib_deps):

        if dep_path == lib_id:
            log.warning('The ID is included?! %s' % lib_path)
            cmd.extend(('-change', dep_path, lib_path))
            continue

        # If the dependency is similarly named to the library itself, then we
        # assume it is its own dependency. Which I don't understand...
        dep_versions = set(name_variants(os.path.basename(dep_path), version_only=True))
        if dep_versions.intersection(id_versions) or dep_versions.intersection(lib_versions):
            log.warning('Library depends on itself?! %s' % dep_path)
            cmd.extend(('-change', dep_path, lib_path))
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
        
        # Go searching for the "best" relocation target.
        # The one with the most defined symbols missing from the lib wins
        # (essentially; it is more complex then that below). We also, dubiously,
        # accept libraries which provide no matching symbols as long as they
        # don't introduct any conflicts. There are a TON of these in FFmpeg.
        best_score = -1
        best_target = None
        seen_targets = set()
        for target in targets:
            if target in seen_targets:
                continue
            seen_targets.add(target)

            if not os.path.exists(target):
                continue
            
            tar_def, tar_undef = get_symbols(target)

            pros   = len(tar_def.intersection(lib_undef))
            shared = len(tar_def.intersection(lib_def))
            cons   = len(lib_undef.intersection(lib_def))
            log.debug('+%d ~%d -%d %s' % (pros, shared, cons, target), verbosity=2)
            if pros - shared - cons > best_score:
                best_score = pros - shared - cons
                best_target = (pros, shared, cons, target)

        if best_target is None:
            log.warning('No relocation targets for %s' % dep_path)
            continue
        if best_score < 0:
            log.warning('No positive relocation targets for %s' % dep_path)
            continue
        
        if best_target[1] or best_target[2]:
            log.warning('Best target has %s collisions for %s' % (best_target[1] + best_target[2], dep_path))

        target = best_target[3]

        log.info('change %s -> %s' % (dep_name, target), verbosity=1)

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

