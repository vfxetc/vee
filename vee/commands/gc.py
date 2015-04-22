import os

from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.cli import style_note
from vee import log


def delete_package(con, id_):
    con.execute('DELETE FROM package_dependencies WHERE depender_id = ? or dependee_id = ?', [id_, id_])
    con.execute('DELETE FROM links WHERE package_id = ?', [id_])
    con.execute('DELETE FROM shared_libraries WHERE package_id = ?', [id_])
    con.execute('DELETE FROM packages WHERE id = ?', [id_])


@command(
    argument('-n', '--dry-run', action='store_true'),
)
def gc(args):

    home = args.assert_home()
    con = home.db.connect()

    with con:

        print style_note('Cleaning installed packages')
        package_ids = []
        install_paths_to_id = {}
        for row in con.execute('SELECT id, name, install_path from packages ORDER by created_at DESC'):

            id_, name, install_path = row
            log.debug('%s %s %s' % (id_, name, install_path))

            if not os.path.exists(install_path):
                print '%s no longer exists at %s; deleting' % (name, install_path)
                if not args.dry_run:
                    delete_package(con, id_)
                    continue

            real_id = install_paths_to_id.get(install_path)
            if real_id:
                print '%s %d is a duplicate of %s; deleting' % (name, id_, real_id)
                # TODO: update any links or package_dependencies which to point to this.
                if not args.dry_run:
                    delete_package(con, id_)
                continue
            install_paths_to_id[install_path] = id_




