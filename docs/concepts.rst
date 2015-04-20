Core Concepts
=============

.. _name:

Names
-----

Package names are currently assumed to existing within a single
namespace, regardless of what type of package they represent. This means that
there are potentially severe collisions between a similarly named package in
Homebrew and on the PyPI, for instance.

The ``--name`` argument is provided to allow for manual disambiguation.

In the future, we may add a concept of namespaces, such that Python projects
exist within a "python" namespace, Ruby gems within "ruby", and Homebrew/others
within "binaries".


Home
----

VEE's home is where it installs and links environments. It is structured like::

    builds/        # Where packages are built; largely temporary.
    dev/           # Where you work as a developer.
    environments/  # The final linked environments you execute in.
    installs/      # The installed (post-build) packages.
    opt/           # Sym-links to last-installed version of every package.
    packages/      # The packages themselves (e.g. tarballs, git repos, etc.).
    repos/         # The requirement repositories which drive your environments.
    src/           # VEE itself.


.. _environment:

Environment
-----------

An environment is a single "prefix", linked from installed packages. Contains
standard top-level directories such as ``bin``, ``etc``, ``lib``, ``include``,
``share``, ``var``, etc..

These are symlinked together using the least number of links possible; a directory
tree that only exists within a single package will be composed of a single
symlink at the root of that tree.

Since their link structure is then unknown, it is highly advised to not write
into an environment.


.. _package:

Packages
--------

Outside of VEE, packages are bundles provided by a remote source which contains
source code, or prepared build artifacts. E.g. a tarball, zipfile, or git repository.

Within VEE, the :class:`Package` class is more abstract, representing both
abstract requirements and a concrete instance of them. It provides all state
required for the various pipelines.


.. _requirement:

Requirement
-----------

A requirement is specification of a package that we would like to have installed
in an environment. These are still represented via the :class:`Package` class.


.. _exec_env:

Execution Environment
---------------------

.. envvar:: VEE_EXEC_ENV

    A comma-delimited list of environment names that were linked into the
    current environment. If you actually use an environment repository, this
    will likely contain ``"NAME/BRANCH"`` of that repo. Each entry here will
    have a corresponding entry in :envvar:`VEE_EXEC_PATH` as well.


.. envvar:: VEE_EXEC_REPO

    A comma-delimited list of environment repository names that were linked
    into the current environment.

.. envvar:: VEE_EXEC_PATH

    A colon-delimited list of paths that are scanned to assemble the current
    environment.

.. envvar:: VEE_EXEC_PREFIX

    The first path scanned to assemble the current environment. This is
    mainly for convenience.

