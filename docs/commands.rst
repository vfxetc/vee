Commands
========

General
-------

``vee init REPO_URL``
~~~~~~~~~~~~~~~~~~~~~

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

``vee install (REQUIREMENT [OPTIONS])+``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install the given requirement or requirements, e.g.::
    
    # Install a single package.
    $ vee install git+git@github.com:westernx/sgmock

    # Install multiple packages.
    $ vee install git+git@github.com:westernx/sgmock git+git@github.com:westernx/sgsession \
        http:/example.org/path/to/tarball.tgz --make-install

    # Install from a requirement set.
    $ vee install path/to/requirements.txt



``vee brew COMMAND+``
~~~~~~~~~~~~~~~~~~~~~

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

``vee repo (init|clone|set|delete|list) [....]``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Manipulate repositories.

::
    # Start a new repo.
    $ vee repo init example

    # Add a new repo, and make it the default.
    $ vee repo clone --default git@github.com:example/myrepo

    # Change a repo's url and branch
    $ vee repo set --branch unstable myrepo

    # Delete a repo.
    $ vee repo delete myrepo

    # List all repos.
    $ vee repo list


``vee git [-r REPO] COMMAND+``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run a ``git`` command on a repository's git repository. (Sorry for the name
collision!)

::

    $ vee git -r primary status
    On branch master
    Your branch is behind 'origin/master' by 1 commit, and can be fast-forwarded.
      (use "git pull" to update your local branch)
    nothing to commit, working directory clean


``vee update``
~~~~~~~~~~~~~~

Update the repositories. This will fail if your repositories are dirty, or have
forked from the remotes.


Development
-----------

``vee develop (init|clone|install|...)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``vee add``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``vee status``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``vee commit``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Environments
------------

``vee upgrade``
~~~~~~~~~~~~~~~

Upgrade environments created from repositories.


``vee link ENVIRON (REQUIREMENT [OPTIONS])+``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Link the given requirement or requirements into the given environment, e.g.::
    
    # Install a single package.
    $ vee link test-environ git+git@github.com:westernx/sgmock

    # Install multiple packages.
    $ vee link test-environ git+git@github.com:westernx/sgmock git+git@github.com:westernx/sgsession \
        http:/example.org/path/to/tarball.tgz --make-install

    # Install from a requirement set.
    $ vee link test-environ path/to/requirements.txt


``vee exec  [-e ENVIRON]+ [-r REPO]+ [-R REQUIREMENTS]+ [NAME=VALUE]+ (--export|COMMAND ARGS*)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Construct an environment, and either export it or run a command in it.

::
    
    # Run in the default repository.
    $ vee exec $command

    # Run within a given repository.
    $ vee exec --repo named_repo $command

    # Run within a named environment.
    $ vee exec -e named_environ $command

    # Run within a constructed runtime for a set of requirements.
    $ vee exec -r requirements.txt $command

    # Export the default environment.
    $ vee exec --export
    export LD_LIBRARY_PATH="/usr/local/vee/lib:$LD_LIBRARY_PATH"
    export PATH="/usr/local/vee/bin:$PATH"
    export PYTHONPATH="/usr/local/vee/lib/python2.7/site-packages"



