import re

from vee.package.requires import RequirementSet
from vee.package.provides import Provision


class SolveError(ValueError):
    pass



def verbose(depth, step, *args):
    print('    ' * depth, step, *args)


def solve(requires, manifest, log=None):
    """Solve abstract requirements into concrete provisions.

    :param dict requires: The abstract requirements to solve.
    :param Manifest manifest: Where to pull packages from.
    :return dict: Concrete provisions that satisfy the abstract requirements.
    :raises SolveError: if unable to satisfy the requirements.

    """

    solved = {}
    to_solve = list(RequirementSet.coerce(requires).items())

    log = log or (lambda *args: None)
    return _solve(solved, to_solve, manifest, log)


def _solve(solved, to_solve, manifest, log, depth=0):

    if not to_solve:
        return solved

    name, reqs = to_solve[0]

    pkg = manifest.get(name)
    if pkg is None:
        raise SolveError("package {!r} does not exist".format(name))

    log(depth, 'start', name, pkg)

    # Make sure it satisfies all solved requirements.
    for prev in solved.values():
        req = prev.requires.get(name)
        if req and not pkg.provides.satisfies(req):
            log(depth, 'fail existing', name, pkg)
            return

    for var in pkg.flat_variants():

        log(depth, 'variant', var)

        # See if it works with the current solution.
        failed = False
        to_solve2 = []

        for name2, req in var.requires.items():

            pkg2 = solved.get(name2)

            log(depth, 'requires', name2, req, pkg2)

            if pkg2 is None:
                # We need to solve this.
                to_solve2.append((name2, req))
                log(depth, 'to solve')

            elif not pkg2.provides.satisfies(req):
                # It doesn't work. Move onto the next one
                failed = True
                log(depth, 'fail')
                break


        if failed:
            continue

        # Go onto the next step.
        solved2 = solved.copy()
        solved2[name] = var
        to_solve2 = to_solve[1:] + to_solve2

        solution = _solve(solved2, to_solve2, manifest, log, depth + 1)
        if solution:
            return solution





