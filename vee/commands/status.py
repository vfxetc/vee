import re

from vee.cli import style, style_error, style_note, style_warning
from vee.commands.main import command, argument
from vee.git import GitRepo, normalize_git_url
from vee.utils import guess_name


def summarize_rev_distance(local, remote, local_name='You', local_verb='are', remote_name='',
    fork_action='please rebase.', ahead_action='you may push.', behind_action='please pull.',
    indent='',
):
    if local and remote:
        print indent + style_warning('%s and the tool have forked%s' % (local_name, '; ' + fork_action if fork_action else '.'))
        print indent + style_warning('There are %d local commit%s, and %d remote commit%s.' % (
            local,
            's' if local > 1 else '',
            remote,
            's' if remote > 1 else '',
        ))
    elif local:
        print indent + style('%s %s ahead%s by %d commit%s%s' % (
            local_name,
            local_verb,
            ' of ' + remote_name if remote_name else '',
            local,
            's' if local > 1 else '',
            '; ' + ahead_action if ahead_action else '.',
        ), fg='green', reset=True)
    elif remote:
        print indent + style_warning('%s %s behind%s by %d commit%s%s' % (
            local_name,
            local_verb,
            ' ' + remote_name if remote_name else '',
            remote,
            's' if remote > 1 else '',
            '; ' + behind_action if behind_action else '.',
        ))


@command(
    argument('--all-dev', action='store_true', help='include all dev packages, not just those in repos'),
    argument('--fetch', action='store_true', help='fetch dev packages'),
    argument('-r', '--repo'),
)
def status(args):

    home = args.assert_home()

    env_repo = home.get_env_repo(args.repo)

    by_name = {}

    # Dev packages.
    for row in home.db.execute('SELECT * FROM dev_packages'):
        row = dict(row)

        dev_repo = GitRepo(row['path'])
        row['remotes'] = dev_repo.remotes()
        by_name.setdefault(row['name'], {})['dev'] = row

    # Current requirements.
    for revision, name in [
        (None, 'work'),
        ('', 'index'),
        ('HEAD', 'head'),
    ]:
        for req in env_repo.reqs(revision=revision).iter_requirements():
            pkg = req.package
            if pkg.type != 'git':
                continue
            pkg.resolve_existing()
            by_name.setdefault(pkg.name, {})[name] = req


    by_name = by_name.items()
    by_name.sort(key=lambda x: x[0].lower())

    for name, everything in by_name:

        dev_row = everything.get('dev')
        work_req = everything.get('work')
        index_req = everything.get('index')
        head_req = everything.get('head')


        if work_req or args.all_dev:

            if dev_row and work_req:
                print '%s %s' % (style('==> ' + name, fg='blue'), work_req)
            elif dev_row:
                print '%s %s' % (style('==> ' + name, fg='blue'), '(dev only)')
            else:
                print '%s %s' % (style('--> ' + name, fg='blue'), work_req)

        if dev_row:

            if not work_req and not args.all_dev:
                continue

            if 'warning' in dev_row:
                print dev_row['warning']

            if 'origin' in dev_row['remotes']:
                dev_row['remote_name'] = 'origin'
            else:
                remote_names = sorted(dev_row['remotes'])
                dev_row['remote_name'] = remote_names[0]
                if len(remote_names) != 1:
                    print style_warning('More that one non-origin remote; picking %s' % dev_row['remote_name'])

        dev_repo = dev_row and GitRepo(dev_row['path'])
        if dev_repo and not dev_repo.exists:
            print style_warning('Git repo does not exist.')
            dev_row = dev_repo = None

        if dev_repo:

            if args.fetch:
                dev_remote_head = dev_repo.fetch(dev_row['remote_name'], 'master')
            else:
                dev_remote_head = dev_repo.rev_parse(dev_row['remote_name'] + '/master')

            # Check your local dev vs. its remote.
            dev_local, dev_remote = dev_repo.distance(dev_repo.head, dev_remote_head)
            summarize_rev_distance(dev_local, dev_remote,
                local_name=name,
                local_verb='is',
                remote_name='%s/master' % dev_row['remote_name'],
            )

            if work_req and work_req.revision:

                # Check your local dev vs the required revision
                pkg_revision = dev_repo.rev_parse(work_req.revision)
                pkg_local, pkg_remote = dev_repo.distance(dev_repo.head, pkg_revision)
                summarize_rev_distance(pkg_local, pkg_remote,
                    local_name=name,
                    local_verb='is',
                    remote_name='"%s" repo' % env_repo.name,
                    ahead_action='you may `vee add %s`' % name,
                )




        # TODO: compare dev vs req
        # TODO: compare dev vs dev's remote


