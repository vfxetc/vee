# encoding: utf8

import datetime
import errno
import fnmatch
import functools
import os
import re
import subprocess
import sys
import threading
import time
import hashlib


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
                    continue
                src_path = os.path.join(src_dir, name)
                dst_path = os.path.join(dst_dir, name)
                if os.path.islink(src_path):
                    rel_link = os.readlink(src)
                    abs_link = os.path.join(src_path, rel_link)
                    os.symlinks(abs_link, dst_path)
                    if is_dir:
                        dont_walk.append(name)
                elif is_dir:
                    makedirs(dst_path)
                else:
                    os.link(src_path, dst_path)
            if dont_walk:
                names[:] = [x for x in names if x not in dont_walk]


class HashingWriter(object):

    def __init__(self, fh, hasher=None):
        self._fh = fh
        self._hasher = hasher or hashlib.sha1()

    def write(self, data):
        self._fh.write(data)
        self._hasher.update(data)

    def hexdigest(self):
        return self._hasher.hexdigest()


def checksum_file(path, hasher=None):
    hasher = hasher or hashlib.sha1()
    with open(path, 'rb') as fh:
        while True:
            chunk = fh.read(16384)
            if not chunk:
                break
            hasher.update(chunk)
    return '%s:%s' % (hasher.name, hasher.hexdigest())

