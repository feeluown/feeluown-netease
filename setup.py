#!/usr/bin/env python3

from setuptools import setup, find_packages


setup(
    name='fuo_netease',
    version='0.9.7',
    description='feeluown netease plugin',
    author='Cosven',
    author_email='yinshaowen241@gmail.com',
    packages=find_packages(exclude=('tests*',)),
    package_data={
        '': ['assets/*.svg',
             ]
        },
    url='https://github.com/feeluown/feeluown-netease',
    keywords=['feeluown', 'plugin', 'netease'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3 :: Only',
    ],
    install_requires=[
        'feeluown>=3.8.12',
        'beautifulsoup4',
        'pycryptodome',
        'marshmallow>=3.0',
        'requests',
        'mutagen>=1.37',
    ],
    extras_require={
        'dev': [
            # lint
            'flake8',

            # unittest
            'pytest>=5.4.0',
            'pytest-cov',
        ],
    },
    entry_points={
        'fuo.plugins_v1': [
            'netease = fuo_netease',
        ]
    },
)
