
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
    vee install homebrew+ffmpeg --configuration '--with-faac'
    
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
    `include`, `share`, `var`, etc..

Requirement:
    A specification of a package that we would like to have installed in an environment.

.. _package:

Package:
    The bundle provided by a remote source which contains source code, or
    prepared build artifacts. E.g. a tarball, zipfile, or git repository.

Manager:
    Wrapper around package managers, but the public API is only for fetching
    packages, and not installing them.


Build Pipeline
--------------

The build pipeline consists of a series of methods, between each the derived
metadata may be re-evaluated allowing for the determination of install paths
later in the pipeline (and so a determination that a package is already
installed may be deferred).

Those methods are, in order:

.. method:: Manager.fetch()

    The :ref:`package <package>` is retrieved and placed at :attr:`Manager.package_path`.
    This step is idempotent (and so is assumed to be called multiple times and
    cache its result).

.. method:: Manager.extract()

    The package's contents ("source") are placed into :attr:`Manager.build_path`
    (which is usually a temporary directory).

.. method:: Manager.build()

    The source is built into a build "artifact".

.. method:: Manager.install()

    The build artifact is installed into :attr:`Manager.install_path`.

.. method:: Environment.link(requirement)

    The build artifact is linked into a final environment.


Names and Paths
~~~~~~~~~~~~~~~

There are a series of ``*_path`` properties on a :class:`Manager`.
They defer to reasonable overrides from a :class:`Requirement`, otherwise
they are discovered by the Manager during the build pipeline.

Internally, Managers provide a ``_derived_*_name`` property which is always
a name derived from currently available information, and a ``_*_name`` property
which defers to reasonable overrides from the Requirement.

Users of the Manager API should only ever use the ``*_path`` properties:

.. attribute:: Manager.package_path

    The location of the package (e.g. archive or git work tree) on disk. This
    must always be correct and never change. Therefore it can only derive from
    the requirement's specification.

.. attribute:: Manager.build_path

    A (usually temporary) directory for building. This must not change once the package
    has been extracted.

.. attribute:: Manager.build_path_to_install

    What part of the build to install. Normally this is the same as ``build_path``,
    but sometimes is a subdirectory.

.. attribute:: Manager.install_path

    The final location of a built artifact. May be ``None`` if it cannot be
    determined. This must not change once installed.



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

