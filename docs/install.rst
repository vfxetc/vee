
Installation
============

VEE is installed via ``pip``. We recommend installing in a clean virtualenv inside the VEE prefix:

.. code-block:: bash

    # Pick the prefix.
    export VEE=/usr/local/vee

    # Create the VEE prefix.
    mkdir -p $VEE
    cd $VEE

    # Create the virtualenv.
    python3 -m venv venv
    source venv/bin/activate

    # Install from source.
    git clone git@github.com:vfxetc/vee src
    pip install -e src

    # Any user who triggers a VEE build process
    # will require write access into the prefix
    sudo chown -R $(whoami):$groupname $VEE
    sudo chmod -R o=rwX,g=rwXs $VEE


Configuration
-------------

VEE takes its base configuration from environment variables. At an absolute minumum, :envvar:`VEE` and :envvar:`VEE_REPO` must be set.

.. envvar:: VEE

    VEE's "prefix". Everything VEE manages will be stored here.

.. envvar:: VEE_REPO

    The default env repo to use. Usually overridable via ``--repo`` flag.

