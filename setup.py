#!/usr/bin/env python3

from setuptools import setup


setup(
    name='fuo_netease',
    version='0.4.2',
    description='feeluown netease plugin',
    author='Cosven',
    author_email='yinshaowen241@gmail.com',
    packages=[
        'fuo_netease',
    ],
    package_data={
        '': []
        },
    url='https://github.com/feeluown/feeluown-netease',
    keywords=['feeluown', 'plugin', 'netease'],
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        ),
    install_requires=[
        'feeluown>=3.3.9',
        'beautifulsoup4',
        'pycryptodome',
        'marshmallow>=3.0',
        'requests',
    ],
    entry_points={
        'fuo.plugins_v1': [
            'netease = fuo_netease',
        ]
    },
)
