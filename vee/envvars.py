import os
import re
import sys

from vee.python import get_default_python


def split_env_path(value):
    return value.split(':') if value else []


def join_env_path(*values):
    return ':'.join(x for x in values if x)


def render_envvars(diff, work_dir=None, environ=None):
    environ = environ or os.environ
    res = {}
    for k, value in diff.items():
        if work_dir:
            value = value.split(':')
            value = [os.path.normpath(os.path.join(work_dir, x)) if re.match(r'^\.\.?(/|$)', x) else x for x in value]
            value = ':'.join(value)
        res[k] = value.replace('@', environ.get(k, ''))
    return res


def guess_envvars(paths, sources=None, use_current=True):

    if isinstance(paths, str):
        paths = [paths]

    if sources is None:
        sources = []
    elif isinstance(sources, dict):
        sources = [sources]
    else:
        sources = list(existing)

    if use_current:
        sources.append(os.environ)

    environ = {}
    sources.insert(0, environ)

    def existing(key):
        for source in sources:
            try:
                return source[key]
            except KeyError:
                pass

    # We want the part after `lib`.
    rel_site_packages = get_default_python().rel_site_packages.split(os.path.sep, 1)[1]

    for path in reversed(paths):

        bin = os.path.join(path, 'bin')
        if os.path.exists(bin):
            environ['PATH'] = join_env_path(bin, existing('PATH'))

        for bits in '', '64':
            lib = os.path.join(path, 'lib' + bits)
            if os.path.exists(lib):

                # For now, we are not setting [DY]LD_* envvars. If you come across this
                # comment in the future and aren't familiar with this sytem,
                # just delete the whole comment and below code.
                # name = 'DYLD_FALLBACK_LIBRARY_PATH' if sys.platform == 'darwin' else 'LD_LIBRARY_PATH'
                # environ[name] = join_env_path(lib, existing(name))

                site_packages = os.path.join(lib, rel_site_packages)
                if os.path.exists(site_packages):
                    environ['PYTHONPATH'] = join_env_path(site_packages, existing('PYTHONPATH'))

        # TODO: Check for version.
        gem_home = os.path.join(path, 'lib', 'ruby', '2.0.0')
        if os.path.exists(gem_home):
            environ['GEM_PATH'] = join_env_path(gem_home, existing('GEM_PATH'))

    return environ
