
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


Examples
--------

::
    vee install homebrew+sqlite
    vee install git+https://github.com/shotgunsoftware/python-api.git
    vee install --force https://github.com/westernx/sgmock/archive/master.zip --install-name sgmock/0.1
    vee install git+git@git.westernx:westernx/sgsession


    vee link example tests/example-env.txt
    vee exec example python -c 'import sgsession; print sgsession.__file__'


Definitions
-----------

Home:
    Where VEE installs and links environments.

Environment:
    A single "prefix", linked from installed packages. Contains `bin`, `etc`, `lib`,
    `include`, `share`, `var`, etc., assemble

Requirement:
    A specification of a package that we would like to have installed in an environment.

.. _package:
Package:
    The bundle provided by a remote source which contains source code, or
    prepared build artifacts.

Manager:
    Wrapper around package managers, but the public API is only for fetching
    packages, and not installing them.


Build Pipeline
--------------

The build pipeline consists of a series of steps, between each the derived
metadata is re-evaluated allowing for the determination of install paths
later in the pipeline (and so a determination that a package is already
installed may be deferred).

Those steps are:

1. ``Manager.fetch()``: The :ref:`package` is retrieved and placed at :ref:`package_path`.
   This step is idempotent (and so is assumed to be called multiple times and
   cache its result).

2. ``Manager.extract()``: The package's contents ("source") are placed into :ref:`build_path`
   (which is usually a temporary directory).

3. ``Manager.build()``: The source is built into a build "artifact".

4. ``Manager.install()``: The build artifact is installed into :ref:`install_path`.

5. ``Environment.link(req)``: The build artifact is linked into a final environment.


Names and Paths
~~~~~~~~~~~~~~~

There are a series of ``*_path`` properties on a :class:`Manager`.
They defer to reasonable overrides from a :class:`Requirement`, otherwise
they are discovered by the Manager.

Internally, Managers provide a ``_derived_*_name`` property which is always
a name derived from currently available information, and a ``_*_name`` property
which defers to reasonable overrides from the Requirement.

Users of the Manager API should only ever use the ``*_path`` properties.

.. _package_path:
``package_path``:
    The location of the package (e.g. archive or git work tree) on disk. This
    must always be correct and static.

.. _build_path:
``build_path``:
    A (usually temporary) directory for building. This must not change once the package
    has been extracted.

.. _install_path:
``install_path``:
    The final location of a built artifact. This must not change once installed.



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

