Pipelines
=========

The package processing pipelines consist of a series of steps, the handlers of
which are determined as the pipeline is processed. This enables us to defer
the build type of a package (e.g. a Python distribution) until after it has
been downloaded and extracted.

There are to main pipelines currently in VEE: the :ref:`install_pipeline` and
:ref:`develop_pipeline`.

All pipelines must start with an "init" step, which must be indempodent, and
may normalize user-specified data on the package (e.g. normalize the URL).


.. _install_pipeline:

Install Pipeline
----------------

The install pipeline is the primary pipeline of VEE, and is reponsible for
installing the packages that are used in the default runtime. It's steps are:

"init"
~~~~~~

Normalizes user-specified data. This step **MUST** be indempodent, as it may run
more than once in common usage. It may also set the package name/path.

"fetch"
~~~~~~~

The package is retrieved and placed at :attr:`Package.package_path`.
This step should be idempotent (and so is assumed to cache its results and
may freely be called multiple times).

"extract"
~~~~~~~~~

The package's contents ("source") are placed into :attr:`Package.build_path`
(which is usually a temporary directory).

"inspect"
~~~~~~~~~

An opportunity to check meta-data and determine self-described dependencies.
This step may also set build and install names/paths.

"build"
~~~~~~~

The source is built into a build "artifact".

"install"
~~~~~~~~~

The build artifact is installed into :attr:`Package.install_path`.

"relocate"
~~~~~~~~~~

Shared libraries are relocated to link against existant libraries (in case
they are not already relocatable, and their dependencies are not in the same
location in all environments).

"optlink"
~~~~~~~~~

The :attr:`Package.install_path` is linked into ``$VEE/opt``, for user
convenience. 


The built-in pipeline looks like:

.. graphviz::

   digraph install_pipeline {

      "git.init" -> "git.fetch";
      "git.fetch" -> "file.extract";

      "generic.init" -> "file.fetch";

      "file.fetch" -> "file.extract";
      "file.fetch" -> "archive.extract";

      "http.init" -> "http.fetch";
      "http.fetch" -> "archive.extract";

      "file.extract" -> "generic.inspect"
      "file.extract" -> "python.inspect"
      "archive.extract" -> "generic.inspect"
      "archive.extract" -> "python.inspect"

      "python.inspect" -> "python.build" -> "python.install"
      "generic.inspect" -> "generic.build" -> "generic.install"
      "generic.inspect" -> "self.build" -> "generic.install"
      "generic.build" -> "self.install"
      "self.build" -> "self.install"

      "generic.inspect" -> "make.build" -> "generic.install"
      "make.build" -> "make.install"

      "python.install" -> "generic.relocate"
      "generic.install" -> "generic.relocate"
      "self.install" -> "generic.relocate"
      "make.install" -> "generic.relocate"

      "homebrew.init" -> "homebrew.fetch" -> "homebrew.extract" -> "homebrew.inspect" -> "homebrew.build" -> "homebrew.install" -> "generic.relocate"

      "generic.inspect" [style=dashed]
      "generic.build" [style=dashed]
      "homebrew.extract" [style=dashed]
      "homebrew.install" [style=dashed]

      "generic.relocate" -> "generic.optlink"





   }



.. _develop_pipeline:

Develop Pipeline
----------------

"init"
~~~~~~

Same as above.

"develop"
~~~~~~~~~

Prepare the package for running in the development environment. Prepare any
generated scripts, perhaps perform a build, and identify any environment
variables to set in order to include this package in the runtime environment.



Names and Paths
---------------

There are a series of ``*_name`` attribute of a :class:`Package`. They are
set from :class:`Requirement` attributes, or self-determined on request via
``Package._assert_names(build=True, ...)``.

There are a series of ``*_path`` properties on a :class:`Package`. They usually
incorporate the corresponding name, but don't have it. They are set from
``Package._assert_paths(build=True, ...)``.

.. warning:: It is very important that an API consumer only every assert the existence of
    names or paths that they are about to use. This allows for the determination
    of some of the names (especially ``install_name`` and ``install_path``) to be
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

.. attribute:: Package.build_subdir

    Where within the build_path to install from. Good for selecting a sub directory
    that the package build itself into.

.. attribute:: Package.install_prefix

    Where within the install_path to install into. Good for installing packages
    into the correct place within the standard tree.


Automatic Building
------------------

Most packages are inspected to determine which style of build to use. Unless
otherwise stated, they will also use an automatic install process as well. The
base styles (in order of inspection) are:


``. vee-build.sh``
~~~~~~~~~~~~~~~~~~

If a ``vee-build.sh`` file exists, it will be sourced and is expected to build
the package. A few environment variables are passed to assist it:

    - ``VEE``
    - ``VEE_BUILD_PATH``
    - ``VEE_INSTALL_NAME``
    - ``VEE_INSTALL_PATH``

The script may export a few environment variables to modify the install
process:

    - ``VEE_build_subdir``
    - ``VEE_install_prefix``


``python setup.py build``
~~~~~~~~~~~~~~~~~~~~~~~~~

If a ``setup.py`` file exists, the package is assumed to be a standard
distutils-style Python package. The build process is to call:

.. code-block:: bash

    python setup.py build

and the install process will be (essentially) to call:

.. code-block:: bash

    python setup.py install --skip-build --single-version-externally-managed


``EGG-INFO`` or ``*.dist-info``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If an ``EGG-INFO`` or ``*.dist-info`` directory exists, the package is
assumed to be a prepared Python package (an Egg or Wheel, respectively), and no
further build steps are taken. The install process will be modified to install
the package contents into ``lib/python2.7/site-packages``.


``./configure``
~~~~~~~~~~~~~~~

If a ``configure`` file exists, it will be executed and passed the install path:

.. code-block:: bash

    ./configure --prefix={package.install_path}

This continues onto the next step...


``make``
~~~~~~~~

If a ``Makefile`` file exists (which may have been constructed by running
``./configure``), ``make`` will be called.


Automatic Installation
----------------------

Unless overridden (either by the package type, or the discovered build type
(e.g. Python packages have their own install process)), the contents of
the build path are copied to the install path, like::

    shutils.copytree(
        os.path.join(pkg.build_path, pkg.build_subdir)),
        os.path.join(pkg.install_path, pkg.install_prefix))
    )

An optional ``--hard-link`` flag indicates that the build and install should
be hard-linked, instead of copied. This results in massive time and space
savings, but requires the packages to be well behaved.


Caveats
-------

``make install``
~~~~~~~~~~~~~~~~

Since we cannot trust that the standard ``make; make install`` pattern will
actually install into a prefix provided to
``./configure``, we do not run ``make install``.

An optional ``--make-install`` flag signals that it is safe to do so.


``python setup.py install``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Instead of running ``python setup.py install``, we break it into
``python setup.py build`` and ``python setup.py install --skip-build``.

Some packages may not like this much.

