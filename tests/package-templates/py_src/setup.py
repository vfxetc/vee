from setuptools import setup, find_packages


setup(

    name='__MOCK_NAME__',
    version='__MOCK_VERSION__' or '1.0.0',

    packages=find_packages(exclude=['build*', 'tests*']),
    
    scripts=['scripts/__MOCK_NAME__'],
    entry_points={
        'console_scripts': '''
            __MOCK_NAME__-ep = __MOCK_NAME__.core:main
        '''
    }
    
)
