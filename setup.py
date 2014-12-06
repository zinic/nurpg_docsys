import os
import sys

import ecad.about

from setuptools import setup, find_packages
from distutils.extension import Extension


def read(relative):
    contents = open(relative, 'r').read()
    return [l for l in contents.split('\n') if l != '']


setup(
    name='ecad',
    version=ecad.about.VERSION,
    description='Event collection and alerting daemon',
    author='John Hopper',
    author_email='john.hopper@rackspace.com',
    url='https://github.rackspace.com/john.hopper/ecad',
    license='Rackspace',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Other Environment',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Cython',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet',
        'Topic :: Utilities'
    ],
    tests_require=read('./project/tests-require.txt'),
    install_requires=read('./project/install-requires.txt'),
    test_suite='nose.collector',
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=['*.tests']))
