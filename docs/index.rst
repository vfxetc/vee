
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

Package:
    The bundle provided by a remote source which contains source code, or
    prepared build artifacts.

Manager:
    Wrapper around package managers, but the public API is only for fetching
    packages, and not installing them.


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

