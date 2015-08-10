
import os
import sys
from argparse import _SubParsersAction

sys.path.append(os.path.abspath(os.path.join(__file__, '..', '..')))


from vee.commands.main import get_parser


def get_sub_action(parser):
    for action in parser._actions:
        if isinstance(action, _SubParsersAction):
            return action



parser = get_parser()

usage = parser.format_usage().replace('usage:', '')
print '''.. _cli_vee:

top-level
---------

::

'''

for line in parser.format_help().splitlines():
    print '    ' + line


subaction = get_sub_action(parser)

for group_name, funcs in parser._func_groups:

    did_header = False

    visible = set(ca.dest for ca in subaction._choices_actions)

    for name, func in funcs:

        if not name in visible:
            continue

        if not did_header:
            print group_name
            print '-' * len(group_name)
            print
            did_header = True

        subparser = subaction._name_parser_map[name]

        print '.. _cli_vee_%s:' % name
        print
        print '``vee %s``' % name
        print '~' * (8 + len(name))
        print
        print '::'
        print
        for line in subparser.format_help().splitlines():
            print '    ' + line
        print

