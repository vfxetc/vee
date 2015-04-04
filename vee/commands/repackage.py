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
from vee.utils import makedirs


PLATFORM_DEPENDENT_EXTS = set(('.so', '.exe', '.dylib', '.a'))


@command(
    argument('-r', '--deps', action='store_true'),
    argument('-f', '--force', action='store_true'),
    argument('-v', '--verbose', action='store_true'),
    argument('-o', '--output'),
    argument('packages', nargs='+'),
)
def repackage(args):

    home = args.assert_home()
    con = home.db.connect()

    if not args.output:
        log.error('--output is required')
        return 1
    makedirs(args.output)

    todo = args.packages
    seen = set()

    while todo:

        desc = todo.pop(0)

        if isinstance(desc, Package):
            pkg = desc
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

        if args.deps:
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

        name = '%s-%s-%s.tgz' % (pkg.name, pkg.revision, sys.platform if platform_dependent else 'any')
        path = os.path.join(args.output, name)

        if os.path.exists(path):
            if args.force:
                os.unlink(path)
            else:
                print '%s already exists' % name
                continue

        if args.verbose:
            print name

        archive = tarfile.open(path, 'w|gz')

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


