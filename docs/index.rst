
VEE: Versioned Execution Environment
====================================


This project aims to encapsulate various package managers in order to allow for
consistent, versioned assembly of an execution environment across a fleet of
OS X and Linux hosts.

Eventually, VEE may provide continuous deployment.

The initial goal is to include packages from:

- Homebrew_ (and linuxbrew_);
- the `Python Package Index <PyPI_>`_;
- ad-hoc Python packages;
- ad-hoc general packages.


Actors
------

Home:
    Where VEE installs and links environments.

Environment:
    A single "prefix", linked from installed packages. Contains `bin`, `etc`, `lib`,
    `include`, `share`, `var`, etc., assemble

Manager:
    Wrapper around package managers, but the public API is only for fetching
    packages, and not installing them.

Package:
    A specification of a single package to install. Determines the manager, and any
    information the Manager will need to install it.

..
    Contents:

    .. toctree::
        :maxdepth: 2

    Indices and tables
    ==================

    * :ref:`genindex`
    * :ref:`modindex`
    * :ref:`search`


.. _Homebrew: http://brew.sh/
.. _linuxbrew: https://github.com/Homebrew/linuxbrew
.. _PyPI: https://pypi.python.org/pypi

