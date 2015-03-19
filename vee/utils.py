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



def find_in_tree(root, name, type='file'):
    pattern = fnmatch.translate(name)
    for dir_path, dir_names, file_names in os.walk(root):
        # Look for the file/directory.
        candidates = dict(file=file_names, dir=dir_names)[type]
        found = next((x for x in candidates if re.match(pattern, x)), None)
        if found:
            return os.path.join(dir_path, found)
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

