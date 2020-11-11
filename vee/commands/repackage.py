from __future__ import print_function

from io import StringIO
import hashlib
import os
import sys
import tarfile
import tempfile
import stat

from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.cli import style, style_note
from vee import log
from vee.package import Package
from vee.utils import makedirs, guess_name, HashingWriter


PLATFORM_DEPENDENT_EXTS = set(('.so', '.exe', '.dylib', '.a'))
PLATFORM_TAG = sys.platform.strip('2')


@command(
    argument('--no-deps', action='store_true', help='skip dependencies'),
    argument('-f', '--force', action='store_true', help='overwrite existing?'),
    argument('-v', '--verbose', action='store_true'),
    argument('-u', '--url', help='base of URL to output for manifest.txt'),
    argument('-d', '--dir', required=True, help='output directory'),
    argument('-e', '--extra', action='append', help='Extra arguments'),
    argument('packages', nargs='+', help='names or URLs'),
)
def repackage(args):

    home = args.assert_home()
    con = home.db.connect()

    makedirs(args.dir)

    todo = args.packages
    seen = set()
    in_order = []
    checksums = {}

    while todo:

        desc = todo.pop(0)

        if isinstance(desc, Package):
            pkg = desc
            pkg.id or pkg.resolve_existing()
        else:
            pkg = Package(name=desc, url='weak', home=home)
            if not pkg.resolve_existing(weak=True):
                pkg = Package(url=desc, home=home)
                if not pkg.resolve_existing():
                    log.error('cannot find package %s' % desc)
                    continue

        if pkg.name in seen:
            continue
        seen.add(pkg.name)

        print(style_note(str(pkg)))

        if not args.no_deps:
            todo.extend(pkg.dependencies)

        platform_dependent = False
        for dir_path, dir_names, file_names in os.walk(pkg.install_path):
            for file_name in file_names:
                _, ext = os.path.splitext(file_name)
                if ext in PLATFORM_DEPENDENT_EXTS:
                    platform_dependent = True
                    break
            if platform_dependent:
                break

        name = '%s-%s-%s.tgz' % (pkg.name, pkg.version, PLATFORM_TAG if platform_dependent else 'any')
        name = name.replace('/', '-') # For taps.
        path = os.path.join(args.dir, name)

        in_order.append((pkg, path))

        if os.path.exists(path):
            if args.force:
                os.unlink(path)
            else:
                print('%s already exists' % name)
                continue

        if args.verbose:
            print(name)

        writer = HashingWriter(open(path, 'wb'), hashlib.md5())
        archive = tarfile.open(fileobj=writer, mode='w|gz')

        for dir_path, dir_names, file_names in os.walk(pkg.install_path):
        
            for dir_name in dir_names:
                path = os.path.join(dir_path, dir_name)
                rel_path = os.path.relpath(path, pkg.install_path)
                if args.verbose:
                    print('    ' + rel_path + '/')
                archive.add(path, rel_path, recursive=False)
            
            for file_name in file_names:
                path = os.path.join(dir_path, file_name)
                mode = os.lstat(path).st_mode
                if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode) or stat.S_ISLNK(mode)):
                    continue
                rel_path = os.path.relpath(path, pkg.install_path)
                if args.verbose:
                    print('    ' + rel_path)
                archive.add(path, rel_path)

        if pkg.dependencies:
            requirements = []
            for dep in pkg.dependencies:
                dep.resolve_existing()
                requirements.append(str(dep))
            buf = StringIO('\n'.join(requirements))
            info = tarfile.TarInfo('vee-manifest.txt')
            info.size = len(buf.getvalue())
            archive.addfile(info, buf)

        archive.close()
        checksums[pkg.name] = 'md5:' + writer.hexdigest()

    print()
    print('Add as requirements in (roughly) the following order:')
    print()
    for pkg, path in reversed(in_order):

        url = (
            args.url.rstrip('/') + '/' + os.path.basename(path)
            if args.url
            else os.path.abspath(path)
        )

        parts = [url, '--name', pkg.name, '--version', pkg.version or '""']
        
        checksum = checksums.get(pkg.name)
        if not checksum and os.path.exists(path):
            hasher = hashlib.md5()
            with open(path, 'rb') as fh:
                while True:
                    chunk = fh.read(16 * 1024 * 1024)
                    if chunk:
                        hasher.update(chunk)
                    else:
                        break
            checksum = 'md5:' + hasher.hexdigest()
        if checksum:
            parts.extend(('--checksum', checksum))

        if args.extra:
            parts.extend(args.extra)

        print(' '.join(parts))


