Commands
========

General
-------

``vee init``
~~~~~~~~~~~~

.. note:: Not finalized.


``vee config``
~~~~~~~~~~~~~~

Manipulate the key-value config; there isn't much here.


``vee doctor``
~~~~~~~~~~~~~~

Self-check.

.. note:: Not finalized.


``vee self-update``
~~~~~~~~~~~~~~~~~~~

Update VEE itself.


Packages
--------

``vee brew``
~~~~~~~~~~~~

Run ``brew`` in the VEE home.


``vee install REQUIREMENT [ARGS]``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install the given requirement.


Repositories
------------

``vee repo``
~~~~~~~~~~~~

Manipulate repositories.

.. note:: Not finalized.


``vee git``
~~~~~~~~~~~

Run ``git`` commands on repositories.


``vee update``
~~~~~~~~~~~~~~

Update the repositories.


Development
-----------

.. note:: These are in heavy development.


Environments
------------

``vee upgrade``
~~~~~~~~~~~~~~~

Upgrade environments created from repositories.


``vee link ENVIRON REQUIREMENT``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Link the given requirement into the given environment.


``vee env ENVIRON``
~~~~~~~~~~~~~~~~~~~

Dump environment variables for the given environment.


``vee prefix ENVIRON``
~~~~~~~~~~~~~~~~~~~~~~

Print the path to the environment.


``vee exec [-e ENVIRON] [-r REQUIREMENTS] COMMAND [...]``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the given command in the given environment.


