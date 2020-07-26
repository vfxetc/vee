import os
import re
from subprocess import check_output, call, check_call


APP = os.path.abspath('SitG.app')
CONTENTS = os.path.join(APP, 'Contents')
OPT = os.path.join(CONTENTS, 'opt')


def walk():
    for dir_path, dir_names, file_names in os.walk('SitG.app'):
        for file_name in file_names:
            if file_name.startswith('.'):
                continue
            path = os.path.join(dir_path, file_name)
            ext = os.path.splitext(file_name)[1]
            # We only want to deal with dynamic libs, or executables.
            if not (ext in ('.so', '.dylib') or not ext and os.access(path, os.X_OK)):
                continue
            yield path


def rewrite(path, original):

    # Strip versioning info.
    original = re.sub(r'\s*\(.+?\)$', '', original.strip())

    # Skip system libs.
    if not original.startswith('/'):
        return original, original
    if re.match(r'^(/System|/usr/lib)', original):
        return original, original

    modified = original
    modified = name_to_path.get(os.path.basename(modified), modified)
    modified = re.sub(r'^/usr/local/lib/(\w+\.framework)/'              , CONTENTS + r'/Frameworks/\1/', modified)
    modified = re.sub(r'^/usr/local/Cellar/(\w+)/[^/]+/(lib|Frameworks)', OPT + r'/\1/\2/', modified)
    modified = re.sub(r'^/usr/local/opt/(\w+)/(lib|Frameworks)/'        , OPT + r'/\1/\2/', modified)

    # Make it relative to the loader.
    if original != modified:
        modified = os.path.join('@loader_path', os.path.relpath(modified, os.path.dirname(path)))

    return original, modified


name_to_path = {}
for path in walk():
    name_to_path[os.path.basename(path)] = path


for path in walk():

    to_print = os.path.relpath(path, OPT)

    # Fix the library's ID/name.
    libname = check_output(['otool', '-D', path]).strip().splitlines()
    libname = libname[1] if len(libname) > 1 else None
    if libname:
        old, new = rewrite(path, libname)
        if new != old:
            if to_print:
                print(to_print)
                to_print = None
            check_call(['install_name_tool', '-id', new, path])

    # Fix all references libraries.
    out = check_output(['otool', '-L', path])
    for line in out.strip().splitlines()[1:]:
        old, new = rewrite(path, line)
        if new != old:
            if to_print:
                print(to_print)
                to_print = None
            check_call(['install_name_tool', '-change', old, new, path])



