#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages
import versioneer

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

with open("requirements.txt", "r") as fh:
    requirements = [line.strip() for line in fh]

test_requirements = []

setup(
    author="Jillian Rowe",
    author_email='jillian@dabbleofdevops.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="A helper function to configure Dask Gateway to play nice with AWS PCluster",
    entry_points={
        'console_scripts': [
            'aws_pcluster_dask_gateway=aws_pcluster_dask_gateway.cli:main',
        ],
    },
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='aws_pcluster_dask_gateway',
    name='aws_pcluster_dask_gateway',
    packages=find_packages(include=['aws_pcluster_dask_gateway', 'aws_pcluster_dask_gateway.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/dabble-of-devops-bioanalyze/aws_pcluster_helpers',
    zip_safe=False,
    # version="0.1.0",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
)
