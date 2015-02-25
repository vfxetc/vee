
.. highlight:: python

VEE: Versioned Execution Environment
====================================


This project aims to encapsulate various package Packages in order to allow for
consistent, versioned assembly of an execution environment across a fleet of
OS X and Linux hosts.

Eventually, VEE may provide continuous deployment.

The initial goal is to include packages from:

- Homebrew_ (and linuxbrew_);
- the `Python Package Index <PyPI_>`_;
- ad-hoc Python packages;
- ad-hoc general packages.


Example
-------

.. code-block:: bash

    # Install VEE.
    export VEE=/usr/local/vee
    sudo mkdir -p $VEE
    sudo chmod -R g=rwXs,o=rwX $VEE
    python <(curl -fsSL https://raw.githubusercontent.com/westernx/vee/master/install_vee.py)
    export PATH="$VEE/src/bin:$PATH"

    # Install some individual packages.
    vee install homebrew+sqlite
    vee install homebrew+ffmpeg --configuration='--with-faac'
    vee install git+https://github.com/shotgunsoftware/python-api.git --name shotgun_api3
    vee install --force https://github.com/westernx/sgmock/archive/master.zip --install-name sgmock/0.1
    vee install git+git@git.westernx:westernx/sgsession

    # Link a few packages into an "example" environment.
    vee link example tests/example-env.txt

    # Execute within the "example" environment.
    vee exec -e example python -c 'import sgmock; print sgmock'


Definitions
-----------

Home:
    Where VEE installs and links environments.

Environment:
    A single "prefix", linked from installed packages. Contains ``bin``, ``etc``, ``lib``,
    ``include``, ``share``, ``var``, etc..

Requirement:
    A specification of a package that we would like to have installed in an environment.

.. _package:

Package:
    A bundle provided by a remote source which contains source code, or
    prepared build artifacts. E.g. a tarball, zipfile, or git repository.
    The :class:`Package` class is slightly more abstract, encapsulating the
    build pipeline for an individual package.


Build Pipeline
--------------

The build pipeline consists of a series of methods, between each the derived
metadata may be re-evaluated allowing for the determination of install paths
later in the pipeline (and so a determination that a package is already
installed may be deferred).

Those methods are, in order:

.. method:: Package.fetch()

    The :ref:`package <package>` is retrieved and placed at :attr:`Package.package_path`.
    This step is idempotent (and so is assumed to be called multiple times and
    cache its result).

.. method:: Package.extract()

    The package's contents ("source") are placed into :attr:`Package.build_path`
    (which is usually a temporary directory).

.. method:: Package.build()

    The source is built into a build "artifact".

.. method:: Package.install()

    The build artifact is installed into :attr:`Package.install_path`.

.. method:: Environment.link(requirement)

    The build artifact is linked into a final environment.



Names and Paths
~~~~~~~~~~~~~~~

There are a series of ``_*_name`` attribute of a :class:`Package`. They are
set from :class:`Requirement` attributes, or self-determined on request via
``Package._assert_names(build=True, ...)``.

There are a series of ``*_path`` properties on a :class:`Package`. They usually
incorporate the corresponding name, but don't have it. They are set from
``Package._assert_paths(build=True, ...)``.

.. warning:: It is very important that an API consumer only every assert the existence of
    names or paths that they are about to use. This allows for the determination
    of some of the names (especially ``_install_name`` and ``install_path``) to be
    deferred as long as possible so that they may use information revealed during
    the earlier of the build pipeline.

The ``*_name`` attributes exist only for the construction of paths; API consumers
should only ever use the ``*_path`` properties:

.. attribute:: Package.package_path

    The location of the package (e.g. archive or git work tree) on disk. This
    must always be correct and never change. Therefore it can only derive from
    the requirement's specification.

.. attribute:: Package.build_path

    A (usually temporary) directory for building. This must not change once the package
    has been extracted.

.. attribute:: Package.install_path

    The final location of a built artifact. May be ``None`` if it cannot be
    determined. This must not change once installed.

.. attribute:: Package.build_subdir_to_install

    Where within the build_path to install from. Good for selecting a sub directory
    that the package build itself into.

.. attribute:: Package.install_subdir_from_build

    Where within the install_path to install into. Good for installing packages
    into the correct place within the standard tree.


Automatic Building
~~~~~~~~~~~~~~~~~~

Most packages are inspected to determine which style of build to use. Unless
otherwise stated, they will also use an automatic install process as well. The
base styles (in order of inspection) are:


``. vee-build.sh``
.....................

If a ``vee-build.sh`` file exists, it will be sourced and is expected to build
the package. A few environment variables are passed to assist it:

    - ``VEE``
    - ``VEE_BUILD_PATH``
    - ``VEE_INSTALL_NAME``
    - ``VEE_INSTALL_PATH``

The script may export a few environment variables to modify the install
process:

    - ``VEE_BUILD_SUBDIR_TO_INSTALL``
    - ``VEE_INSTALL_SUBDIR_FROM_BUILD``


``python setup.py build``
............................

If a ``setup.py`` file exists, the package is assumed to be a standard
distutils-style Python package. The build process is to call:

.. code-block:: bash

    python setup.py build

and the install process will be (essentially) to call:

.. code-block:: bash

    python setup.py install --skip-build --single-version-externally-managed


``*.egg-info`` or ``*.dist-info``
.................................

If an ``*.egg-info`` or ``*.dist-info`` directory exists, the package is
assumed to be a prepared Python package (an Egg or Wheel, respectively), and no
further build steps are taken. The install process will be modified to install
the package contents into ``lib/python2.7/site-packages``.


``./configure``
...................

If a ``configure`` file exists, it will be executed and passed the install path:

.. code-block:: bash

    ./configure --prefix={package.install_path}

This continues onto the next step...


``make``
............

If a ``Makefile`` file exists (which may have been constructed by running
``./configure``), ``make`` will be called.


Automatic Installation
~~~~~~~~~~~~~~~~~~~~~~

Unless overridden (either by the package type, or the discovered build type
(e.g. Python packages have their own install process)), the contents of
the build path are copied to the install path, like::

    shutils.copytree(
        os.path.join(pkg.build_path, pkg.build_subdir_to_install)),
        os.path.join(pkg.install_path, pkg.install_subdir_from_build))
    )


Caveats
~~~~~~~

``make install``
................

Since we cannot trust that the standard ``make; make install`` pattern will
actually install into a prefix provided to
``./configure``, we do not run ``make install``.


``python setup.py install``
...........................

Instead of running ``python setup.py install``, we break it into
``python setup.py build`` and ``python setup.py install --skip-build``.

Some packages may not like this much.



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

