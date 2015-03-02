Commands
========

General
-------

``vee init``
~~~~~~~~~~~~

Initialize the structures, and setup the primary repository. This should be
run before any other commands.

::

    $ export VEE=/usr/local/vee
    $ vee init git@git.westernx:westernx/vee-repo
    Initializing "primary" tests/sandbox/vee


..
    ``vee config``
    Manipulate the key-value config; there isn't much here.


``vee doctor``
~~~~~~~~~~~~~~

Perform self-checks. This isn't very substantial yet; the idea is to add checks
here as bugs come up.

::
    
    $ vee doctor
    Home: /usr/local/vee
    Default repo: primary git@git.westernx:westernx/vee-repo
    OK


``vee self-update``
~~~~~~~~~~~~~~~~~~~

Update VEE itself. This effectively runs ``install_vee.py`` with a few default
arguments.

::

    $ vee self-update
    Fetching updates from remote repo
    From https://github.com/westernx/vee
     * branch            master     -> FETCH_HEAD
    Updating to master  
    HEAD is now at 01234567 Example commit message.
    Cleaning ignored files
    Performing self-check
    Done!  


Packages
--------

``vee install REQUIREMENT [ARGS]``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install the given requirement.


``vee brew``
~~~~~~~~~~~~

Run a command on VEE's Homebrew. This is sometimes nessesary to manage Homebrew
dependencies, as they are generally outside of the standard build pipeline.

::
    
    $ vee brew install sqlite
    ==> Installing sqlite dependency: readline
    ==> Installing sqlite

    $ vee brew list
    readline sqlite



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


