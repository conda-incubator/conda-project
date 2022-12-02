# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from setuptools import find_packages, setup

import versioneer

with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = [
    "conda-lock>=1.2",
    "lockfile",
    "pexpect",
    "ruamel.yaml",
    "pydantic",
    "shellingham",
]
docs_requirements = [
    "Sphinx>=5.1.1",
    "sphinx-autobuild>=2021.3.14",
    "sphinx-autodoc-typehints>=^1.19.2",
    "myst-parser>=0.18.0",
    "pydata-sphinx-theme>=0.9.0",
]

setup(
    name="conda-project",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Tool for encapsulating, running, and reproducing projects with Conda environments",
    license="BSD",
    author="Albert DeFusco",
    author_email="adefusco@anaconda.com",
    url="https://github.com/AlbertDeFusco/conda-project",
    packages=find_packages(),
    entry_points={"console_scripts": ["conda-project=conda_project.cli.main:main"]},
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "docs": docs_requirements,
    },
    keywords="conda-project",
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
)
