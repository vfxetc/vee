import os
from setuptools import setup, find_packages


here = os.path.abspath(os.path.join(__file__, '..'))

about_path = os.path.join(here, 'vee', '__about__.py')
about_ns = {}
execfile(about_path, {'__file__': about_path}, about_ns)

setup(

    name='vee',
    version=about_ns['__version__'],
    description='Versioned Execution Environment',
    url='http://github.com/westernx/vee',
    
    packages=find_packages(exclude=['build*', 'tests*']),
    
    author='Mike Boers',
    author_email='vee@mikeboers.com',
    license='BSD-3',
    
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],

    # scripts=['bin/vee'],
    
    entry_points=open(os.path.join(here, 'vee', 'entry_points.txt')).read(),
    
    
)
