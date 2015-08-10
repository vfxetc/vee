import os
import sys

from vee.commands.main import command, argument


@command(
    name='self-update',
    help='update vee itself',
    aliases=['selfupdate'],
    group='setup',
)
def self_update(args):
    """Update VEE itself. This effectively runs `install_vee.py` with a few
    default arguments, or is the same as `git pull` in the `src` directory.

    """

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
