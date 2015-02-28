'''usage: python install.py

This script may be run on its own, or straight from GitHub, e.g.:

    python <(curl -fsSL https://raw.githubusercontent.com/westernx/vee/master/install_vee.py)

To install to /usr/local/vee, and force an update to the latest version:

    python <(curl -fsSL https://raw.githubusercontent.com/westernx/vee/master/install_vee.py) --yes


'''

def ANSI(*args):
    return ''.join('\x1b[' + str(x) for x in args)
def SGR(*args):
    return ''.join(ANSI(str(x) + 'm') for x in args)

red    = lambda x: SGR(1, 31) + x + SGR(0)
green  = lambda x: SGR(1, 32) + x + SGR(0)
yellow = lambda x: SGR(1, 33) + x + SGR(0)
blue   = lambda x: SGR(1, 34) + x + SGR(0)
bold   = lambda x: SGR(1) + x + SGR(0)
faint  = lambda x: SGR(2) + x + SGR(0)


def heading(heading, msg='', detail=''):
    print blue(heading), bold(msg), detail

def error(msg, detail=''):
    print red("Error:"), bold(msg), detail

def warning(msg, detail=''):
    print yellow('Warning:'), bold(msg), detail


import sys

if sys.version_info < (2, 7):
    error("VEE requires Python 2.7")
    exit(1)

from subprocess import call, check_call, check_output, PIPE
import argparse
import errno
import os
import shutil
import tarfile
import urllib2
import zipfile


def makedirs(x):
    try:
        os.makedirs(x)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


class SwitchAction(argparse.Action):

    def __init__(self, option_strings, **kwargs):
        kwargs['nargs'] = 0
        self.option_values = {}
        for opt in option_strings[:]:
            self.option_values[opt] = True
            if opt.startswith('--'):
                false_opt = '--no-' + opt[2:]
                self.option_values[false_opt] = False
                option_strings.append(false_opt)
        super(SwitchAction, self).__init__(option_strings, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, self.option_values[option_string])


def main(argv=None):

    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', help='where to install vee')

    parser.add_argument('--url', default='https://github.com/westernx/vee.git')
    parser.add_argument('--branch', default='master')

    parser.add_argument('--force', action=SwitchAction, help='install over local changes')
    parser.add_argument('--bashrc', action=SwitchAction, help='add vee to your ~/.bashrc file')
    parser.add_argument('-y', '--yes', action='store_true', help='automatically confirm all prompts')

    args = parser.parse_args(argv)


    def get_arg(key, message, default):
        value = getattr(args, key)
        if value is not None:
            return value
        if args.yes:
            return default
        print '%s [%s]:' % (green(message), faint(default)),
        res = raw_input().strip()
        return res or default

    def prompt_bool(message):
        if args.yes:
            return True
        while True:
            print '%s [%s]:' % (green(message), faint('Yn')),
            res = raw_input().strip().lower()
            if res in ('', 'y', 'yes'):
                return True
            if res in ('n', 'no'):
                return False

    def prompt_switch(key, message):
        value = getattr(args, key)
        if value is not None:
            return value
        return prompt_bool(message)


    # Running as root is scary.
    if not os.getuid():
        warning('Running as root is dangerous.')
        if not prompt_bool('Continue anyways?'):
            return

    # Make sure we have git.
    if not check_output(['which', 'git']):
        error('git was not found; cannot continue.')
        return 2

    # Determine where to install.
    prefix = args.prefix or os.environ.get('VEE')
    if not prefix:
        prefix = get_arg('prefix', 'Where should we install VEE?', '/usr/local/vee')
    prefix = os.path.abspath(prefix)

    if not os.path.exists(os.path.dirname(prefix)):
        warning('Directory above install location does not exist.')
        if not prompt_bool('Are you sure you want to create it?'):
            return

    # Create directory and set permissions.
    if not os.access(prefix, os.W_OK):
        warning('No write access to %s' % os.path.dirname(prefix))
        if not prompt_bool('Use sudo to make the directory?'):
            return
        check_output(['sudo', 'mkdir', '-p', prefix])
        check_output(['sudo', 'chown', str(os.getuid()), prefix])
    else:
        makedirs(prefix)

    vee_src = os.path.join(prefix, 'src')

    # Init or clone the repo.
    git_dir = os.path.join(vee_src, '.git')
    if not os.path.exists(vee_src):
        heading('Cloning', args.url)
        check_call(['git', 'clone', args.url, vee_src])
    else:
        if not os.path.exists(git_dir):
            heading('Initing repo on top of existing')
            check_call(['git', '--git-dir', git_dir, '--work-tree', vee_src, 'init'])
            check_call(['git', '--git-dir', git_dir, '--work-tree', vee_src, 'config', 'remote.origin.url', args.url])
            check_call(['git', '--git-dir', git_dir, '--work-tree', vee_src, 'config', 'remote.origin.fetch', '+refs/heads/*:refs/remotes/origin/*'])

    # Assert the repo is clean.
    status = check_output(['git', '--git-dir', git_dir, '--work-tree', vee_src, 'status', '--porcelain']).strip()
    if status:
        warning('Repository is not clean.')
        if not prompt_switch('force', 'Would you like to continue? All changes will be lost.'):
            return

    # Fetch and reset.
    heading('Fetching updates from remote repo')
    check_call(['git', '--git-dir', git_dir, '--work-tree', vee_src, 'fetch', args.url, args.branch])
    heading('Updating to master')
    check_call(['git', '--git-dir', git_dir, '--work-tree', vee_src, 'reset', '--hard', 'FETCH_HEAD'])
    heading('Cleaning ignored files')
    check_call(['git', '--git-dir', git_dir, '--work-tree', vee_src, 'clean', '-dxf'], stdout=PIPE)

    # Basic sanity checks.
    heading('Performing self-check')
    if not os.path.exists(os.path.join(vee_src, 'vee', '__init__.py')):
        error('Repository does not appear to be vee; cannot continue.')
        return 3
    out = check_output([os.path.join(vee_src, 'bin', 'vee'), 'doctor', '--ping'])
    if out.strip() != 'pong':
        error('Basic self-check did not pass; try `vee doctor --ping`')
        return 4

    shell_lines = [
        'export VEE="%s"' % prefix,
        'export PATH="$VEE/src/bin:$PATH" # Add VEE to your environment',
    ]

    if prompt_switch('bashrc', 'Append to your ~/.bashrc?'):

        heading('Adding VEE to your ~/.bashrc')
        print yellow('Note:'), bold('You may need to open a new terminal, or `source ~/.bashrc`, for VEE to work.')

        bashrc = os.path.expanduser('~/.bashrc')
        if os.path.exists(bashrc):
            lines = list(open(bashrc))
        else:
            lines = []

        # Strip out existing config.
        lines = [
            line for line in lines if
            not (line.startswith('export VEE="') or line.startswith('export PATH="$VEE'))
        ]
        
        content = ''.join(lines).rstrip() + '\n\n' + '\n'.join(shell_lines) + '\n'
        with open(bashrc, 'w') as fh:
            fh.write(content)


    elif os.environ.get('VEE', '') != prefix:
        heading('Add the following to your environment:')
        for line in shell_lines:
            print '    ' + line.split('#')[0]


    heading('Done!')


if __name__ == '__main__':
    exit(main() or 0)
