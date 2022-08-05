from setuptools import setup

setup(
    name='dspl',
    version='0.1',
    py_modules=['dspl'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        dspl=dspl:core.cli
    ''',
)
