'''usage: python install.py

This script may be run on its own, or straight from GitHub, e.g.:

    python <(curl -fsSL https://raw.githubusercontent.com/westernx/vee/master/install.py)

To install to /usr/local/vee, and force an update to the latest version:

    python <(curl -fsSL https://raw.githubusercontent.com/westernx/vee/master/install.py) --yes


'''

from subprocess import call, check_output
import argparse
import errno
import glob
import os
import shutil
import tarfile
import tempfile
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


parser = argparse.ArgumentParser()
parser.add_argument('--prefix')

parser.add_argument('--git-repo', default='https://github.com/westernx/vee.git')
parser.add_argument('--need-git', action='store_true', help='only install if git is availible')

parser.add_argument('--archive', default='https://github.com/westernx/vee/archive/master.zip', 
    help='archive to use if git is not availible')

parser.add_argument('--force', action=SwitchAction, help='delete existing installation')
parser.add_argument('--bashrc', action=SwitchAction, help='add vee to your ~/.bashrc file')
parser.add_argument('-y', '--yes', action='store_true', help='automatically confirm all prompts')

args = parser.parse_args()


def get_arg(key, message, default):
    value = getattr(args, key)
    if value is not None:
        return value
    if args.yes:
        return default
    print '%s [%s]:' % (message, default),
    res = raw_input().strip()
    return res or default


def switch(key, message):
    value = getattr(args, key)
    if value is not None:
        return value
    if args.yes:
        return True
    while True:
        print '%s [Yn]:' % message,
        res = raw_input().strip().lower()
        if res in ('', 'y', 'yes'):
            return True
        if res in ('n', 'no'):
            return False


prefix = os.path.abspath(get_arg('prefix', 'Where should we install VEE?', '/usr/local/vee'))
makedirs(prefix)

vee_src = os.path.join(prefix, 'src')


if check_output(['which', 'git']):
    if not os.path.exists(vee_src):
        print 'Cloning', args.git_repo
        call(['git', 'clone', args.git_repo, vee_src])
    else:
        git_dir = os.path.join(vee_src, '.git')
        if not os.path.exists(git_dir):
            print 'Initing repo on top of existing'
            call(['git', '--git-dir', git_dir, '--work-tree', vee_src, 'init'])
        print 'Fetching updates'
        call(['git', '--git-dir', git_dir, '--work-tree', vee_src, 'config', 'remote.origin.url', args.git_repo])
        call(['git', '--git-dir', git_dir, '--work-tree', vee_src, 'config', 'remote.origin.fetch', '+refs/heads/*:refs/remotes/origin/*'])
        call(['git', '--git-dir', git_dir, '--work-tree', vee_src, 'fetch', 'origin'])
        print 'Resetting...'
        call(['git', '--git-dir', git_dir, '--work-tree', vee_src, 'reset', '--hard', 'origin/master'])


else:

    print 'Git was not found.'
    if args.need_git:
        print 'Cannot continue without git.'
        exit(4)

    # Blast out existing.
    if os.path.exists(vee_src):
        print 'VEE is already installed.'
        if not switch('force', 'Delete existing installation?'):
            exit()
        shutil.rmtree(vee_src)

    # Download the new one.
    print 'Downloading', args.archive
    res = urllib2.urlopen(args.archive)
    base, ext = os.path.splitext(os.path.basename(args.archive.split('?')[0]))
    tmp_src_root = os.path.join(prefix, 'tmp', 'vee-%s-%s' % (base, os.urandom(4).encode('hex')))
    makedirs(tmp_src_root)
    tmp_archive = tmp_src_root + ext
    with open(tmp_archive, 'wb') as fh:
        for chunk in iter(lambda: res.read(8192), ''):
            fh.write(chunk)

    # Unarchive.
    if ext == '.zip':
        zip_ = zipfile.ZipFile(tmp_archive)
        zip_.extractall(tmp_src_root)
    elif ext in ('.tgz', '.tar.gz'):
        tar = tarfile.open(tmp_archive)
        tar.extractall(tmp_src_root)
    else:
        print 'Cannot expand %r archive' % ext.strip('.')
        exit(2)

    # Find setup.py, and copy its directory to the final location.
    for tmp_src, dir_names, file_names in os.walk(tmp_src_root):
        if 'vee' in dir_names and 'setup.py' in file_names:
            break
    else:
        print 'Archive does not appear to be vee; exiting.'
        exit(3)
    shutil.copytree(tmp_src, vee_src)



shell_lines = [
    'export VEE="%s"' % prefix,
    'export PATH="$VEE/src/bin:$PATH" # Add VEE to your environment',
]

if switch('bashrc', 'Append to your ~/.bashrc?'):

    print 'Adding VEE to your ~/.bashrc'
    print 'NOTE: You may need to open a new terminal, or `source ~/.bashrc`, for VEE to work.'

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


else:
    print 'Add the following to your environment:'
    for line in shell_lines:
        print '    ' + line.split('#')[0]


