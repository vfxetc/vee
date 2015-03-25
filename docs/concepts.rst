Core Concepts
=============

.. _name:

Names
-----

Requirement/Package names are currently assumed to existing within a single
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


Environments
------------

An environment is a single "prefix", linked from installed packages. Contains
standard top-level directories such as ``bin``, ``etc``, ``lib``, ``include``,
``share``, ``var``, etc..

These are linked together using the least number of links possible. Since their
link composition is then unknown, it is highly advised that code does not write
into an environment.

Requirements
------------

A requirement is specification of a package that we would like to have installed
in an environment.


.. _package:

Packages
--------

Packages are bundles provided by a remote source which contains source code, or
prepared build artifacts. E.g. a tarball, zipfile, or git repository. The
:class:`Package` class is slightly more abstract, encapsulating the build
pipeline for an individual package.
