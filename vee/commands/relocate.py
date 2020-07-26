import os
import stat

from vee.cli import style
from vee.commands.main import command, argument
from vee.home import PRIMARY_REPO
from vee import libs
from vee import log


@command(
    argument('-n', '--dry-run', action='store_true'),
    argument('--scan', action='store_true', help='look for installed libraires'),
    argument('--rescan', action='store_true', help='redo previous scans'),
    argument('--spec', default='AUTO'),
    argument('path', nargs='?'),
    help='relocate a package',
    group='plumbing',
)
def relocate(args):

    home = args.assert_home()

    if args.scan or args.rescan:
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

            print(install_path)

            found = libs.get_installed_shared_libraries(home.db.connect(), package_id, install_path, rescan=args.rescan)
            for lib in found:
                print('    ' + lib)

        return


    if args.path:
        con = home.db.connect()
        target_cache = {}
        libs.relocate(os.path.abspath(args.path), con, spec=args.spec, dry_run=args.dry_run, target_cache=target_cache)




