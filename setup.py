#!/usr/bin/env python
import os
import setuptools

PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))

requirements = []
with open(os.path.join(PROJECT_ROOT, 'requirements.txt')) as f:
    for line in f:
        line = line.strip()

        if not line or line.startswith('#') or line.startswith('-e'):
            continue

        requirements.append(line)

setuptools.setup(
    name='falcon_heavy',
    use_scm_version=True,
    description='Tool for Falcon API calls validation by OpenApi specification',
    author='Ingate Development Team',
    author_email='idev.tech@ingate.ru',
    url='https://www.ingate.ru/',
    packages=setuptools.find_packages(exclude=('tests', 'tests.*')),
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=requirements,
    setup_requires=['setuptools_scm'],
)
