import os
from setuptools import setup, find_packages


here = os.path.abspath(os.path.join(__file__, '..'))

about_path = os.path.join(here, 'vee', '__about__.py')
about = {}
exec(compile(open(about_path).read(), about_path, 'exec'), {'__file__': about_path}, about)


setup(

    name='vee',
    version=about['__version__'],
    description='Versioned Execution Environments',
    url='http://github.com/vfxetc/vee',
    
    packages=find_packages(exclude=['build*', 'tests*']),
    
    author='Mike Boers',
    author_email='vee@mikeboers.com',
    license='BSD-3',
    
    install_requires=[
        'setuptools',
        'packaging',
        'wheel',
        'virtualenv', # TODO: Use stdlib venv.
        'urllib3',
    ],

    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Version Control',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Software Distribution',
    ],
    
    entry_points='''

        [console_scripts]

        vee = vee.commands.main:main


        [vee_commands]

        # General
        init = vee.commands.init:init
        config = vee.commands.config:config
        doctor = vee.commands.doctor:doctor
        self-update = vee.commands.self_update:self_update
        gc = vee.commands.gc:gc
        list = vee.commands.list:list_
        repackage = vee.commands.repackage:repackage

        rezpack = vee.commands.rez:rezpack

        # Requirements.
        install = vee.commands.install:install

        # Environments.
        link = vee.commands.link:link
        relocate = vee.commands.relocate:relocate
        exec = vee.commands.exec_:exec_

        # Underlying commands.
        brew = vee.commands.brew:brew
        git = vee.commands.git:git
        sqlite3 = vee.commands.sqlite3:sqlite3

        # Development.
        add = vee.commands.add:add
        commit = vee.commands.commit:commit
        develop = vee.commands.develop:develop
        edit = vee.commands.edit:edit
        push = vee.commands.push:push
        repo = vee.commands.repo:repo
        status = vee.commands.status:status
        update = vee.commands.update:update
        upgrade = vee.commands.upgrade:upgrade

        # Remote Management
        client = vee.commands.client:client
        server = vee.commands.server:server


        [vee_pipeline_steps]

        # External package managers.
        homebrew = vee.pipeline.homebrew:HomebrewManager
        gem = vee.pipeline.gem:GemManager
        rpm = vee.pipeline.rpm:RPMChecker

        # Transports.
        file = vee.pipeline.file:FileTransport
        git  = vee.pipeline.git:GitTransport
        http = vee.pipeline.http:HttpTransport
        pypi = vee.pipeline.pypi:PyPiTransport

        # Extractors.
        archive = vee.pipeline.archive:ArchiveExtractor

        # Builds.
        generic = vee.pipeline.generic:GenericBuilder
        make    = vee.pipeline.make:MakeBuilder
        python  = vee.pipeline.python:PythonBuilder
        self    = vee.pipeline.self:SelfBuilder

        # Internal
        deferred = vee.pipeline.deferred:DeferredStep

    '''
    
)
