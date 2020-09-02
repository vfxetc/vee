import re

from vee.semver import Version, VersionExpr
from vee.package.requires import Requires


class SolveError(ValueError):
    pass



def solve_dependencies(requires, manifest):
    """Solve abstract requirements into concrete provisions.

    :param dict requires: The abstract requirements to solve.
    :param Manifest manifest: Where to pull packages from.
    :return dict: Concrete provisions that satisfy the abstract requirements.
    :raises SolveError: if unable to satisfy the requirements.

    """

