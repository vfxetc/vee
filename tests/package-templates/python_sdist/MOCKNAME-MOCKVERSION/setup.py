from setuptools import setup, find_packages


setup(

    name='MOCKNAME',
    version='MOCKVERSION' or '1.0.0',

    packages=find_packages(exclude=['build*', 'tests*']),
    
    scripts=['scripts/MOCKNAME'],
    entry_points={
        'console_scripts': '''
            MOCKNAME-ep = MOCKNAME.core:main
        '''
    }
    
)
