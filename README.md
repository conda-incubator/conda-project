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

### Tests

To run tests you can either activate the env and run pytest

```
conda activate ./env
pytest
```

or use `conda run`

 ```
 conda run --no-capture-output -p ./env pytest
 ```

### Linting

This project uses [pre-commit](https://pre-commit.com/) to aid with linting.
Pre-Commit is configured to run
* [isort](https://pycqa.github.io/isort/)
* [black](https://black.readthedocs.io/en/stable/)
* [flake8](https://flake8.pycqa.org/en/latest/)

This repository is configured with [Pre-Commit.ci](https://pre-commit.ci/), which
will automatically fix Pull Requests to comply with the above linters.

The pre-commit Conda package is included in the development environment.yml file.
To install the hooks in your local clone run

```
conda run --no-capture-output -p ./env pre-commit install
```

Once configured the pre-commit hooks are run automatically, but you can run
them manually with

```
conda run --no-capture-output -p ./env pre-commit run --all-files
```
