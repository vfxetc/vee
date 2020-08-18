.. highlight:: python

.. _index:

VEE: Versioned Execution Environments
=====================================

This project wraps existing package managers and software build mechanisms in order to allow for consistent, versioned assembly of execution environments across a fleet of cross-platform hosts.

VEE sources packages from:

- Homebrew_
- `The Python Package Index <PyPI_>`_
- RubyGems_
- ad-hoc ``git``, ``http``, and local packages

and will build packages using:

- ``python setup.py build``
- ``make``
- ``cmake``
- or custom build scripts


Contents
--------

.. toctree::
    :maxdepth: 2

    install
    workflow
    concepts
    pipeline
    commands


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. todolist::


.. _Homebrew: http://brew.sh/
.. _PyPI: https://pypi.org/
.. _RubyGems: https://rubygems.org/

