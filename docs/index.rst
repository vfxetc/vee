
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



Contents
========

.. toctree::
    :maxdepth: 2

    pipeline
    commands


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. todolist::


.. _Homebrew: http://brew.sh/
.. _linuxbrew: https://github.com/Homebrew/linuxbrew
.. _PyPI: https://pypi.python.org/pypi

