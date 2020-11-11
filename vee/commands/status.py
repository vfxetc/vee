from __future__ import print_function

import difflib
import os
import re

from vee.cli import style, style_error, style_note, style_warning
from vee.commands.main import command, argument
from vee.exceptions import format_cli_exc
from vee.git import GitRepo, normalize_git_url
from vee.packageset import PackageSet
from vee.utils import guess_name


def summarize_rev_distance(local, remote, local_name='You', local_verb='are', remote_name='',
    fork_action='please rebase.', ahead_action='you may push.', behind_action='please pull.',
    indent='    ',
):
    if local and remote:
        print(indent + style_warning('%s and %s have forked%s' % (local_name, remote_name or 'the remote', '; ' + fork_action if fork_action else '.')))
        print(indent + style_warning('There are %d local commit%s, and %d remote commit%s.' % (
            local,
            's' if local > 1 else '',
            remote,
            's' if remote > 1 else '',
        )))
    elif local:
        print(indent + style('%s %s ahead%s by %d commit%s%s' % (
            local_name,
            local_verb,
            ' of ' + remote_name if remote_name else '',
            local,
            's' if local > 1 else '',
            '; ' + ahead_action if ahead_action else '.',
        ), fg='green', reset=True))
    elif remote:
        print(indent + style_warning('%s %s behind%s by %d commit%s%s' % (
            local_name,
            local_verb,
            ' ' + remote_name if remote_name else '',
            remote,
            's' if remote > 1 else '',
            '; ' + behind_action if behind_action else '.',
        )))


@command(
    argument('--all-dev', action='store_true', help='include all dev packages, not just those in repos'),
    argument('--fetch', action='store_true', help='fetch dev packages'),
    argument('-v', '--verbose', action='count'),
    argument('-r', '--repo'),
    argument('names', nargs='*'),
)
def status(args):

    home = args.assert_home()

    env_repo = home.get_env_repo(args.repo)
    pkg_set = PackageSet(home=home)

    by_name = {}

    # Dev packages.
    for dev_repo in home.iter_development_packages():
        by_name.setdefault(dev_repo.name, {})['dev'] = dev_repo

    # Current requirements.
    for revision, name in [
        (None, 'work'),
        ('HEAD', 'head'),
    ]:
        for req in env_repo.load_manifest(revision=revision).iter_packages():
            pkg = pkg_set.resolve(req, check_existing=False)
            if pkg.fetch_type != 'git':
                continue
            by_name.setdefault(pkg.name, {})[name] = req


    by_name = list(by_name.items())
    by_name.sort(key=lambda x: x[0].lower())

    if args.names:
        by_name = [x for x in by_name if x[0] in args.names]

    for name, everything in by_name:

        dev_repo = everything.get('dev')
        work_req = everything.get('work')
        head_req = everything.get('head')

        has_dev = dev_repo is not None
        only_has_dev = has_dev and not (work_req or head_req)

        # Skip dev-only stuff most of the time.
        if only_has_dev and not args.all_dev:
            continue

        # Title.
        print('%s %s' % (
            style('%s %s' % ('==>' if has_dev else '-->', name), fg='blue'),
            '(dev only)' if only_has_dev else ''
        ))

        # Status of requirements.
        if work_req and head_req and str(work_req) == str(head_req):
            if args.verbose:
                print('=== %s' % work_req)
        else:

            # Print a lovely coloured diff of the specific arguments that
            # are changing.
            # TODO: make this environment relative to the context.
            head_args = head_req.to_args(exclude=('base_environ', )) if head_req else []
            work_args = work_req.to_args(exclude=('base_environ', )) if work_req else []
            differ = difflib.SequenceMatcher(None, head_args, work_args)
            opcodes = differ.get_opcodes()
            if head_req is not None:
                print(style('---', fg='red', bold=True), end=' ')
                for tag, i1, i2, j1, j2 in opcodes:
                    if tag in ('replace', 'delete'):
                        print(style(' '.join(head_args[i1:i2]), fg='red', bold=True))
                    elif tag in ('equal', ):
                        print(' '.join(head_args[i1:i2]), end=' ')
            if work_req is not None:
                print(style('+++', fg='green', bold=True), end=' ')
                for tag, i1, i2, j1, j2 in opcodes:
                    if tag in ('replace', 'insert'):
                        print(style(' '.join(work_args[j1:j2]), fg='green', bold=True))
                    elif tag in ('equal', ):
                        print(' '.join(work_args[j1:j2]), end=' ')

        if dev_repo:

            remotes = dev_repo.remotes()

            if 'origin' in remotes:
                dev_repo._st_remote_name = 'origin'
            else:
                remote_names = sorted(remotes)
                dev_repo._st_remote_name = remote_names[0]
                if len(remote_names) != 1:
                    print('    ' + style_warning('More that one non-origin remote; picking %s' % dev_row['remote_name']))

        if dev_repo:

            if dev_repo.status():
                print('    ' + style_warning('Work tree is dirty.'))

            branch = dev_repo.get_current_branch()
            ref = '{}/{}'.format(dev_repo._st_remote_name, branch)
            if args.fetch:
                dev_remote_head = dev_repo.fetch(dev_repo._st_remote_name, branch)
            else:
                dev_remote_head = dev_repo.rev_parse(ref)

            # Check your local dev vs. its remote.
            dev_local, dev_remote = dev_repo.distance(dev_repo.head, dev_remote_head)
            summarize_rev_distance(dev_local, dev_remote,
                local_name=name,
                local_verb='is',
                remote_name=ref,
                behind_action='please pull or `vee dev ff %s`' % name,
            )

        if dev_repo and work_req and work_req.revision:

            # Check your local dev vs the required revision
            try:
                pkg_revision = dev_repo.rev_parse(work_req.revision)
                pkg_local, pkg_remote = dev_repo.distance(dev_repo.head, pkg_revision)
                summarize_rev_distance(pkg_local, pkg_remote,
                    local_name=name,
                    local_verb='is',
                    remote_name='%s repo' % env_repo.name,
                    ahead_action='you may `vee add %s`' % name,
                    behind_action='please `vee dev checkout --repo %s %s`' % (env_repo.name, name),
                )

            except Exception as e:
                print('    ' + format_cli_exc(e))

        # TODO: Warn if you have added something to the repo, but not pushed it.

