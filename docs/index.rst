.. highlight:: python

.. _index:

VEE: Versioned Execution Environment
====================================

This project aims to encapsulate various package in order to allow for
consistent, versioned assembly of an execution environment across a fleet of
OS X and Linux hosts.

The initial goal is to source packages from:

- Homebrew_
- `The Python Package Index <PyPI_>`_
- RubyGems_
- ad-hoc ``git``, ``http``, and local packages

and to build packages using:

- ``python setup.py build``
- ``make``
- ``cmake``
- or custom build scripts


Contents
========

.. toctree::
    :maxdepth: 2

    workflow
    concepts
    pipeline
    commands
    python_api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. todolist::


.. _Homebrew: http://brew.sh/
.. _PyPI: https://pypi.org/
.. _RubyGems: https://rubygems.org/

