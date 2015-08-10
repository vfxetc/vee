import os
import re
import shutil

from vee.commands.main import command, argument, group
from vee.environment import Environment
from vee.cli import style_note, style_warning
from vee import log


def delete_environment(con, id_):
    con.execute('DELETE FROM links WHERE environment_id = ?', [id_])
    con.execute('DELETE FROM environments WHERE id = ?', [id_])

def delete_package(con, id_):
    con.execute('DELETE FROM package_dependencies WHERE depender_id = ? or dependee_id = ?', [id_, id_])
    con.execute('DELETE FROM links WHERE package_id = ?', [id_])
    con.execute('DELETE FROM shared_libraries WHERE package_id = ?', [id_])
    con.execute('DELETE FROM packages WHERE id = ?', [id_])


@command(

    argument('-e', '--prune-environments', action='store_true'),
    argument('--keep-latest', type=int, default=10),

    argument('-p', '--prune-orphaned-packages', action='store_true'),

    argument('-n', '--dry-run', action='store_true'),

    group='plumbing',
    help='cleanup VEE',

)
def gc(args):

    home = args.assert_home()
    con = home.db.connect()

    with con:

        repo_ids = {}
        for row in con.execute('SELECT id, name from repositories'):
            repo_ids[row['name']] = row['id']

        envs_by_id = {}

        log.info(style_note('Cleaning environments'))
        for row in con.execute('SELECT id, name, path, repository_id from environments ORDER BY created_at ASC'):
            
            id_, name, path, repo_id = row
            
            if not os.path.exists(path):
                log.info('environment does not exist at %s; deleting' % (path))
                if not args.dry_run:
                    delete_environment(con, id_)
                continue

            # Track for later.
            envs_by_id.setdefault(repo_id, []).append((id_, name, path))

            # The rest is making sure the repo_id and commit are correct.
            if repo_id:
                continue

            m = re.match(r'(\w+)/commits/([0-9a-f]{7,8}(?:-dirty)?)$', name)
            if not m:
                log.warning('%s (%d) does not appear to be managed by git; skipping' % (name, id_))
                continue

            repo_name, commit_name = m.groups()
            repo_id = repo_ids.get(repo_name)
            if not repo_id:
                log.warning('repo %s does not exist for %s (%d); skipping' % (repo_name, name, id_))
                continue

            log.info('Fixing repo relationship for %s (%d)' % (name, id_))
            if not args.dry_run:
                con.execute('UPDATE environments SET repository_id = ?, repository_commit = ? WHERE id = ?', [
                    repo_id, commit_name, id_
                ])

        if args.prune_environments:
            log.info(style_note('Pruning old environments'))
            for repo_id, envs in sorted(envs_by_id.iteritems()):
                for id_, name, path in envs[:-args.keep_latest]:
                    log.info('Deleting %s (%d)' % (name, id_))
                    if not args.dry_run:
                        shutil.rmtree(path)
                        delete_environment(con, id_)

        log.info(style_note('Cleaning installed packages'))
        package_ids = []
        install_paths_to_id = {}
        for row in con.execute('SELECT id, name, install_path, build_path from packages ORDER by created_at DESC'):

            id_, name, install_path, build_path = row
            log.debug('%s %s %s' % (id_, name, install_path))

            if not os.path.exists(install_path):
                log.info('%s no longer exists at %s; deleting' % (name, install_path))
                if not args.dry_run:
                    delete_package(con, id_)
                    continue

            real_id = install_paths_to_id.get(install_path)
            if real_id:
                log.info('%s %d is a duplicate of %s; deleting' % (name, id_, real_id))
                # TODO: update any links or package_dependencies which to point to this.
                if not args.dry_run:
                    delete_package(con, id_)
                continue
            install_paths_to_id[install_path] = id_

            if args.prune_orphaned_packages:
                row = con.execute('SELECT count(1) FROM links WHERE package_id = ?', [id_]).fetchone()
                if not row[0]:
                    log.info('%s (%d) is not linked; deleting' % (name, id_))
                    if not args.dry_run:
                        if build_path and os.path.exists(build_path):
                            shutil.rmtree(build_path)
                        shutil.rmtree(install_path)
                        delete_package(con, id_)






