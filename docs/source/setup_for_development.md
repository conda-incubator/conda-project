# Setup for development

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

## Tests

To run tests you can either activate the env and run pytest

```
conda activate ./env
pytest
```

or use `conda run`

 ```
 conda run --no-capture-output -p ./env pytest
 ```

## Linting

This project uses [pre-commit](https://pre-commit.com/) to aid with linting.
Pre-Commit is configured to run
* [isort](https://pycqa.github.io/isort/)
* [black](https://black.readthedocs.io/en/stable/)
* [flake8](https://flake8.pycqa.org/en/latest/)

This repository is configured with [Pre-Commit.ci](https://pre-commit.ci/), which
will automatically fix Pull Requests to comply with the above linters.

The pre-commit conda package is included in the development environment.yml file.
To install the hooks in your local clone run

```
conda run --no-capture-output -p ./env pre-commit install
```

Once configured the pre-commit hooks are run automatically, but you can run
them manually with

```
conda run --no-capture-output -p ./env pre-commit run --all-files
```

## Documentation

To develop the documentation, you can run the following command from the project root:

```shell
make -C docs html
```

To develop with live-updating documentation, run:

```shell
make -C docs live
```
