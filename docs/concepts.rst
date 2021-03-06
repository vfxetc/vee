Core Concepts
=============

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


.. _requirements:

Requirement Specification
-------------------------

Requirements are specified via a series of command-line-like arguments.
The first is a URL, which may be HTTP, common git formats, or VEE-specific, e.g.:

- ``http://cython.org/release/Cython-0.22.tar.gz``
- ``git+git@github.com:vfxetc/sitetools``
- ``pypi:pyyaml``

The requirements are further refined by the following arguments:

.. include:: _build/requirements.inc

These may be passed to individual commands, e.g.::

    vee link pypi:pyyaml --version=3.11

or via a ``manifest.txt`` file, which contains a list of requirements.


.. _manifest_txt:

``manifest.txt``
--------------------

The manifest file may also include:

    - Headers, which are lines formatted like ``Header: Value``, e.g.::

        Name: example
        Version: 0.43.23
        Vee-Revision: 0.1-dev+4254bc1

    - Comments beginning with ``#``;
    - Basic control flow, starting with ``%``, e.g.:

      ::

        # For the Shotgun cache:
        % if os.environ.get('VEEINCLUDE_SGCACHE'):
            git+git@github.com:vfxetc/sgapi --version=6da9d1c5
            git+git@github.com:vfxetc/sgcache --version=cd673656
            git+git@github.com:vfxetc/sgevents --version=a58e61c5
        % endif


.. _name:

Name Conflicts
--------------

Package names are currently assumed to existing within a single
namespace, regardless of what type of package they represent. This means that
there are potentially severe collisions between a similarly named package in
Homebrew and on the PyPI, for instance.

The ``--name`` argument is provided to allow for manual disambiguation.


.. _env_repo:

Environment Repository
----------------------

An environment repository is a git repository which contains (at a minimum)
a :ref:`manifest_txt` file.

They are managed by the :ref:`cli_vee_repo` command.


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

