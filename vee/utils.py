# encoding: utf8

import datetime
import errno
import fnmatch
import functools
import hashlib
import itertools
import os
import re
import stat
import subprocess
import sys
import threading
import time
import ssl



class cached_property(object):
    
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
    
    def __get__(self, instance, owner_type=None):
        if instance is None:
            return self
        try:
            return instance.__dict__[self.__name__]
        except KeyError:
            value = self.func(instance)
            instance.__dict__[self.__name__] = value
            return value


def makedirs(*args):
    path = os.path.join(*args)
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e
    return path


def chmod(path, specs, recurse=False):

    if isinstance(specs, basestring):
        specs = specs.split(',')

    ops = []
    for spec in specs:
        m = re.match(r'([augo]*)([=+-])([rwx]*)$', spec.strip())
        if not m:
            raise ValueError('Bad chmod request.', spec)
        raw_who, op, raw_mode = m.groups()

        if raw_who == 'a' or not raw_who:
            raw_who = 'ugo'

        mask = 0
        value = 0

        for who in 'usr', 'grp', 'oth':

            if raw_who and who[0] not in raw_who:
                continue

            mask |= getattr(stat, 'S_IRWX{}'.format(who[0].upper()))

            for mode in 'rwx':
                if mode not in raw_mode:
                    continue
                value |= getattr(stat, 'S_I{}{}'.format(mode.upper(), who.upper()))

        ops.append((op, mask, value))

    if not recurse:
        _chmod(path, ops)
        return

    for root, dir_names, file_names in os.walk(path):
        for name in itertools.chain(dir_names, file_names):
            _chmod(os.path.join(root, name), ops)


def _chmod(path, ops):

    st = os.stat(path)
    new_mode = old_mode = stat.S_IMODE(st.st_mode)

    for op, mask, value in ops:

        masked   = new_mode & mask
        unmasked = new_mode & (~mask)

        if op == '+':
            masked |= value
        elif op == '=':
            masked = value
        elif op == '-':
            masked &= ~value
        else:
            raise ValueError('Unknown chmod op.', op)

        new_mode = masked | unmasked

    if new_mode != old_mode:
        os.chmod(path, new_mode)


_FIND_SKIP_DIRS = frozenset(('.git', '.svn'))

def find_in_tree(root, name, type='file'):
    pattern = fnmatch.translate(name)
    for dir_path, dir_names, file_names in os.walk(root):

        # Look for the file/directory.
        candidates = dict(file=file_names, dir=dir_names)[type]
        found = next((x for x in candidates if re.match(pattern, x)), None)
        if found:
            return os.path.join(dir_path, found)

        # We need to skip .git directories, just in case they are in our
        # tarballs.
        dir_names[:] = [x for x in dir_names if x not in _FIND_SKIP_DIRS]

        # Bail when we hit a fork in the directory tree.
        if len(dir_names) > 1 or file_names:
            return


def guess_name(path):

    path = re.sub(r'[#?].+$', '', path) # Query strings and fragments.
    path = re.sub(r'(\.[\w-]+)+$', '', path) # Extensions.
    path = re.sub(r'([._-])v?\d+(\.|\d|$).*$', '', path) # Version numbers.
    path = re.sub(r'([._-])[._-]+', r'\1', path) # Collapse punctuation.

    part_iter = reversed(re.split(r'[@:/+]', path)) # Split!
    part_iter = (re.sub(r'(^\W+|\W+$)', '', x) for x in part_iter) # Strip outer punctuation.
    part_iter = (x for x in part_iter if x) # Skip empties.

    return next(part_iter).lower()


def linktree(src, dst, symlinks=False, ignore=None):
    if not symlinks:
        raise NotImplementedError('symlinks')
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    for src_dir, dir_names, file_names in os.walk(src):
        dst_dir = os.path.join(dst, os.path.relpath(src_dir, src))

        if ignore is not None:
            ignored_names = ignore(src_dir, dir_names + file_names)
        else:
            ignored_names = set()

        for is_dir, names in ((True, dir_names), (False, file_names)):
            dont_walk = set()
            for name in names:
                if name in ignored_names:
                    if is_dir:
                        dont_walk.add(name)
                    continue
                src_path = os.path.join(src_dir, name)
                dst_path = os.path.join(dst_dir, name)
                if os.path.islink(src_path):
                    rel_link = os.readlink(src)
                    abs_link = os.path.join(src_path, rel_link)
                    os.symlinks(abs_link, dst_path)
                    if is_dir:
                        dont_walk.add(name)
                elif is_dir:
                    makedirs(dst_path)
                else:
                    try:
                        os.link(src_path, dst_path)
                    except:
                        print 'Error during: os.link(%r, %r)' % (src_path, dst_path)
                        raise
            if dont_walk:
                names[:] = [x for x in names if x not in dont_walk]


class HashingWriter(object):

    def __init__(self, fh, hasher=None):
        self._fh = fh
        self._hasher = hasher or hashlib.md5()

    def write(self, data):
        self._fh.write(data)
        self._hasher.update(data)

    def hexdigest(self):
        return self._hasher.hexdigest()


def _checksum_file(path, hasher=None):
    hasher = hasher or hashlib.md5()
    with open(path, 'rb') as fh:
        while True:
            chunk = fh.read(16384)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.name, hasher.hexdigest()

def checksum_file(path, hasher=None):
    return '%s:%s' % _checksum_file(path, hasher)

def assert_file_checksum(path, checksum):
    m = re.match(r'^(md5|sha1)[:=]([0-9a-fA-F]+)$', checksum)
    if not m:
        raise ValueError('unknown checksum format %r' % checksum)
    name, hash1 = m.groups()
    _, hash2 = _checksum_file(path, getattr(hashlib, name)())
    if hash1 != hash2:
        raise ValueError('%s:%s does not match expected %s' % (name, hash2, checksum))


DB_NAME = 'vee-index.sqlite'

def default_home_path(environ=None):
    try:
        return (environ or os.environ)['VEE']
    except KeyError:
        return find_home()

def find_home(default_here=False):
    root = here = os.path.abspath(os.path.join(__file__, '..', '..', '..'))
    while root and root != os.path.sep:
        if os.path.exists(os.path.join(root, DB_NAME)):
            return root
        root = os.path.dirname(root)
    if default_here:
        return here


_httplib3_global_pool = None

def http_pool():
    global _httplib3_global_pool
    if _httplib3_global_pool is None:
        import urllib3 # Need to defer because _bootstrap import utils.
        _httplib3_global_pool = urllib3.PoolManager()
    return _httplib3_global_pool

def http_request(*args, **kwargs):
    return http_pool().request(*args, **kwargs)



