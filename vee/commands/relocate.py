import os
import stat

from vee.cli import style
from vee.commands.main import command, argument
from vee.home import PRIMARY_REPO
from vee.libs import find_libraries, find_package_libraries, get_dependencies


@command(
    argument('--scan', action='store_true'),
    argument('--rescan', action='store_true'),
    argument('--ignore-existing', action='append'),
    argument('path', nargs='?'),
    help='relocate a package',
)
def relocate(args):

    home = args.assert_home()

    if args.scan:
        rows = list(home.db.execute(
            '''SELECT id, install_path FROM packages
            ORDER BY created_at DESC
        '''))
        seen_paths = set()
        for row in rows:

            package_id, install_path = row
            if not os.path.exists(install_path):
                continue
            if install_path in seen_paths:
                continue
            seen_paths.add(install_path)

            print install_path

            libs = find_package_libraries(home, install_path, package_id, force=args.rescan)
            for lib in libs:
                print '    ' + lib

    targets_by_name = {}
    con = home.db.connect()

    if args.path:
        for lib_path in find_libraries(os.path.abspath(args.path)):
            lib_stat = os.lstat(lib_path)
            if stat.S_ISLNK(lib_stat.st_mode):
                continue
            print lib_path
            for dep_path in get_dependencies(lib_path):

                ignore_existing = args.ignore_existing and any(dep_path.startswith(x) for x in args.ignore_existing)
                if not ignore_existing and os.path.exists(dep_path):
                    continue

                print '    ' + dep_path

                dep_name = os.path.basename(dep_path)
                if dep_name not in targets_by_name:
                    targets = targets_by_name[dep_name] = []
                    for row in con.execute('''SELECT
                        packages.install_path, installed_libraries.rel_path
                        FROM packages JOIN installed_libraries
                        ON packages.id = installed_libraries.package_id
                        WHERE installed_libraries.name = ?
                        ORDER BY packages.created_at DESC
                    ''', [dep_name]):
                        target_path = os.path.join(row[0], row[1])
                        targets.append(target_path)

                targets = targets_by_name[dep_name]

                if not targets:
                    # print '        could not find target'
                    continue

                print '        ' + targets[0]



