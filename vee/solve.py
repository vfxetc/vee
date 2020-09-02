import re

from vee.semver import Version, VersionExpr
from vee.package.requires import RequirementSet
from vee.package.provides import Provision


class SolveError(ValueError):
    pass



def solve_dependencies(requires, manifest):
    """Solve abstract requirements into concrete provisions.

    :param dict requires: The abstract requirements to solve.
    :param Manifest manifest: Where to pull packages from.
    :return dict: Concrete provisions that satisfy the abstract requirements.
    :raises SolveError: if unable to satisfy the requirements.

    """

    solved = {}
    to_solve = list(RequirementSet.coerce(requires).items())

    _solve(solved, to_solve, manifest)


def _solve(solved, to_solve, manifest):

    for name, reqs in to_solve:

        pkg = manifest.get(name)
        if pkg is None:
            raise SolveError("package {} does not exist".format(name))

        print("HERE 1", name, pkg)

        # For each variant, we test if it works with the current solution.
        # If it does, then we go onto the next step.
        # If none result in a solution, we bail.
        for var in pkg.flat_variants():
            print("HERE 2", name, var)
        else:
            return # failure






