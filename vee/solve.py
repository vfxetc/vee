import re

from vee.package.requires import RequirementSet
from vee.package.provides import Provision


class SolveError(ValueError):
    pass



def verbose(depth, step, *args):
    print('    ' * depth, step, *args)


def solve(*args, **kwargs):
    """Solve abstract requirements into concrete provisions.

    :param RequirementSet requires: The abstract requirements to solve.
    :param Manifest manifest: Where to pull packages from.
    :return dict: Concrete provisions that satisfy the abstract requirements.
    :raises SolveError: if unable to satisfy the requirements.
    
    """
    return next(iter_solve(*args, **kwargs), None)


def iter_solve(requires, manifest, log=verbose):

    done = {}
    todo = list(RequirementSet.coerce(requires).items())

    log = log or (lambda *args: None)
    return _solve(done, todo, manifest, log)


def _solve(done, todo, manifest, log, depth=0):

    if not todo:
        yield done
        return

    name, reqs = todo[0]

    pkg = manifest.get(name)
    if pkg is None:
        raise SolveError("package {!r} does not exist".format(name))

    log(depth, 'start', name, pkg)

    # Make sure it satisfies all solved requirements.
    for prev in done.values():
        req = prev.requires.get(name)
        if req and not pkg.provides.satisfies(req):
            log(depth, 'fail existing', name, pkg)
            return

    for var in pkg.flat_variants():

        log(depth, 'variant', var)

        failed = False
        next_todo = []

        for name2, req in var.requires.items():

            pkg2 = done.get(name2)

            log(depth, 'requires', name2, req, pkg2)

            if pkg2 is None:
                # We need to solve this.
                # We don't grab it immediately, because we want to do a
                # breadth-first search.
                log(depth, 'to solve')
                next_todo.append((name2, req))

            elif not pkg2.provides.satisfies(req):
                # This variant doesn't work with the already done packages;
                # move onto the next one.
                log(depth, 'fail variant')
                failed = True
                break

        if failed:
            continue

        # Go a step deeper.
        # We clone everything so that the call stack maintains the state we
        # need to keep going from here.
        next_done = done.copy()
        next_done[name] = var
        next_todo = todo[1:] + next_todo

        yield from _solve(next_done, next_todo, manifest, log, depth + 1)





