
import os
import sys
from argparse import _SubParsersAction, RawDescriptionHelpFormatter, SUPPRESS

sys.path.append(os.path.abspath(os.path.join(__file__, '..', '..')))


from vee.package import requirement_parser as parser

formatter = RawDescriptionHelpFormatter('manifest.txt')


for action in parser._actions:

    if action.dest in ('url', ):
        continue
    if action.help == SUPPRESS:
        continue

    print('.. _requirement_arg_%s:' % action.dest)
    print()

    lines = formatter._format_action(action).splitlines()

    print('``%s``' % lines[0])
    #print '~' * (4 + len(lines[0]))
    print()
    print('\n'.join(lines[1:]))
    print()

#for line in parser.format_help().splitlines():
#    print '    ' + line

