import os
import sys

from vee import _vendor

import pkg_resources


def _bootstrap_entrypoints():

    # See if we are already registered.
    req = pkg_resources.Requirement.parse('vee')
    dist = pkg_resources.working_set.find(req)
    if dist is not None:
        return

    # Make a dummy metadata provider (which looks in our package for metadata),
    # and a dummy distribution (which lives wherever it does on dist).
    class Provider(pkg_resources.DefaultProvider):
        egg_info = os.path.abspath(os.path.join(__file__, '..', '_egg-info'))
    dummy = pkg_resources.Distribution(
        project_name='vee',
        version='99.99.99',
        metadata=Provider('vee'),
        location=os.path.abspath(os.path.join(__file__, '..', '..')),
    )
    pkg_resources.working_set.add(dummy)


_bootstrap_entrypoints()
