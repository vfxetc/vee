from cStringIO import StringIO
import os
import sys
import tarfile
import tempfile

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
    argument('-u', '--url', help='base of URL to output for requirements.txt'),
    argument('-d', '--dir', required=True, help='output directory'),
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

        print style_note(str(pkg))

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

        name = '%s-%s-%s.tgz' % (pkg.name, pkg.revision, PLATFORM_TAG if platform_dependent else 'any')
        path = os.path.join(args.dir, name)

        in_order.append((pkg, path))

        if os.path.exists(path):
            if args.force:
                os.unlink(path)
            else:
                print '%s already exists' % name
                continue

        if args.verbose:
            print name

        writer = HashingWriter(open(path, 'wb'))
        archive = tarfile.open(fileobj=writer, mode='w|gz')

        for dir_path, dir_names, file_names in os.walk(pkg.install_path):
            for file_name in file_names:
                file_path = os.path.join(dir_path, file_name)
                rel_path = os.path.relpath(file_path, pkg.install_path)
                if args.verbose:
                    print '    ' + rel_path
                archive.add(file_path, rel_path)

        if pkg.dependencies:
            requirements = []
            for dep in pkg.dependencies:
                dep.resolve_existing()
                requirements.append(str(dep))
            buf = StringIO('\n'.join(requirements))
            info = tarfile.TarInfo('vee-requirements.txt')
            info.size = len(buf.getvalue())
            archive.addfile(info, buf)

        archive.close()
        checksums[pkg.name] = 'sha1=' + writer.hexdigest()

    print
    print 'Add as requirements in (roughly) the following order:'
    print
    for pkg, path in reversed(in_order):

        checksum = checksums.get(pkg.name)
        url = (
            args.url.rstrip('/') + '/' + os.path.basename(path)
            if args.url
            else os.path.abspath(path)
        )

        parts = [url, '--name', pkg.name, '--revision', pkg.revision or '""']
        if checksum:
            parts.extend(('--checksum', checksum))

        print ' '.join(parts)


