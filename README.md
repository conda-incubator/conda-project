# Conda Project

[![codecov](https://codecov.io/gh/conda-incubator/conda-project/branch/main/graph/badge.svg?token=XNRS8JKT75)](https://codecov.io/gh/conda-incubator/conda-project)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/conda-incubator/conda-project/main.svg)](https://results.pre-commit.ci/latest/github/conda-incubator/conda-project/main)

Tool for encapsulating, running, and reproducing projects with Conda environments

This package is intended as a successor to [Anaconda Project](https://github.com/Anaconda-Platform/anaconda-project).
Please continue to use Anaconda Project until it has been delcared deprecated and Conda Project has
stabilized.

## Setup for development

To setup conda-project for development, first install [Miniconda](https://docs.conda.io/en/latest/miniconda.html),
then

1. Clone this repository.
1. Create a development environment using the `environment.yml` file in this repository
    ```
    conda env create -p ./env
1. Install `conda-project` as editable in the env by activating the environment first
    ```
    conda activate ./env
    pip install -e .
    ```
1. To run tests you can either activate the env and run pytest
    ```
    conda activate ./env
    pytest
    ```

    or use `conda run`

    ```
    conda run -p ./env pytest
    ```
