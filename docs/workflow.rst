Workflows
=========


User Workflow
-------------

.. code-block:: bash
    
    # Before your first use of vee, it must be initialized. This command
    # will error if already run, with no ill effects.
    vee init

    # Add the environment repository (replace with your git remote and name),
    # and build it.
    vee repo clone git@github.com:vfxetc/vee-repo vfxetc
    vee upgrade

    # Run some installed commands.
    vee exec COMMAND
    #   or:
    eval "$(vee exec --export)"
    COMMAND
    #   or:
    vee exec --export >> ~/.bashrc
    COMMAND

    # Whenever there are changes to the environment repo, you must "update"
    # to fetch the changes, and "upgrade" to build the environment.
    vee update
    vee upgrade



Developer Workflow
------------------

.. code-block:: bash

    # Specify where you want your dev packages to be, if not in $VEE/dev.
    export VEE_DEV=~/dev

    # Install a package for development. This must be a package that is
    # referred to by the default repository.
    vee develop install PACKAGE

    cd ~/dev/PACKAGE

    # Develop here; use `dev` to run in the dev environment.
    dev MY_COMMAND

    # Commit your changes to the package.
    git commit -am 'What you did to PACKAGE.'

    # Commit your changes to the VEE repo.
    vee add PACKAGE
    vee commit --patch -m 'Did something to PACKAGE.'

    # Test locally.
    vee upgrade
    MY_COMMAND

    # Push out the package, and repo.
    git push
    vee push



Manual Workflow
---------------

.. code-block:: bash

    # Install some individual packages into the default environment.
    # These will be lost upon the next "upgrade".
    vee link homebrew+sqlite
    vee link homebrew+ffmpeg --configuration='--with-faac'
    vee link git+https://github.com/shotgunsoftware/python-api.git --name shotgun_api3
    vee link --force https://github.com/vfxetc/sgmock/archive/master.zip --install-name sgmock/0.1
    vee link git+git@github.com:vfxetc/sgsession

    # Link a few packages into an "example" environment.
    vee link -e example examples/basic.txt

    # Execute within the "example" environment.
    vee exec -e example python -c 'import sgmock; print sgmock'

