import os
import sys

from vee.commands.main import command, argument


@command(
    name='self-update',
    help='update vee itself',
)
def self_update(args):

    args.assert_home()

    try:
        import install_vee
    except ImportError:
        root = os.path.abspath(os.path.join(__file__, '..', '..', '..'))
        sys.path.append(root)
        import install_vee

    install_vee.main([
        '--prefix', args.home.root,
        '--no-bashrc',
    ])
