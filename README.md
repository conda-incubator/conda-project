# conda-project

[![codecov](https://codecov.io/gh/conda-incubator/conda-project/branch/main/graph/badge.svg?token=XNRS8JKT75)](https://codecov.io/gh/conda-incubator/conda-project)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/conda-incubator/conda-project/main.svg)](https://results.pre-commit.ci/latest/github/conda-incubator/conda-project/main)

Tool for encapsulating, running, and reproducing projects with conda environments.

This package is intended as a successor to [Anaconda Project](https://github.com/Anaconda-Platform/anaconda-project).

## Why?

Sharing your work is more than sharing your code in a script file or notebook. To make your work properly reproducible, it is necessary to include the list of required third-party dependencies, specifications for how to run your code, and
any other files that it may need.

See [8 Levels of Reproduciblity](https://www.anaconda.com/blog/8-levels-of-reproducibility) for an in-depth
discussion of the differences between "It works for me." to "I've made sure that anyone can reliably execute my work."
Conda Project is a framework that aims to help you to ensure a high degree of reproducibility in the projects you
create.

## Installation

You can install conda-project using the conda package manager:

```text
conda install -c conda-forge conda-project
```

## Quick start

Let's start a new project using Python, Pandas, and Jupyter Notebooks.
The commands below will work on terminals in Mac, Linux, and Windows.
For Windows you can use either `cmd.exe` or Powershell.

We first create a directory and initialize a new project, which will create a new conda environment and lock the dependencies:

```text
(base) > conda project init --directory my-project python=3.9 notebook pandas
Locking dependencies for environment default on platforms osx-64, osx-arm64, linux-64, win-64: done
Project created at /Users/adefusco/Development/conda-incubator/conda-project/examples/my-project
```

The goal of Conda Project is to maintain a conda enviroment specifically for the new `my-project` directory.
You'll see that this directory contains it's own `environment.yml` file a [Conda Lock](https://conda.github.io/conda-lock/) file and a `conda-project.yml`
file. You can learn more about these files in the [User Guide](https://conda-incubator.github.io/conda-project/user_guide.html)

```text
(base) > tree ./
├── conda-project.yml
├── default.conda-lock.yml
├── environment.yml
```

You can activate the environment, which will install packages locally to this project according to the lock file.
Notice that after running `conda project activate` the shell prompt switches to `(default)`, which is the name
of the local environment for this project.

```text
(base) > cd my-project
(base) > conda project activate

Downloading and Extracting Packages


Downloading and Extracting Packages

Preparing transaction: done
Verifying transaction: done
Executing transaction: done
environment created at /Users/adefusco/Development/conda-incubator/conda-project/examples/my-project/envs/default
## Project environment default activated in a new shell.
## Exit this shell to de-activate.
```

And in the activated environment you can launch editors or run commands. For example, since we included
the `notebook` package we can launch Jupyter Notebook from the activated environment:

```text
(default) > jupyter notebook
[I 12:23:03.632 NotebookApp] Serving notebooks from local directory: /Users/adefusco/Development/conda-incubator/conda-project/examples/my-project
[I 12:23:03.632 NotebookApp] Jupyter Notebook 6.5.2 is running at:
[I 12:23:03.632 NotebookApp] http://localhost:8888/?token=1208a3441039526c03b44c233f07436321ad4fd3cced443d
[I 12:23:03.632 NotebookApp]  or http://127.0.0.1:8888/?token=1208a3441039526c03b44c233f07436321ad4fd3cced443d
[I 12:23:03.632 NotebookApp] Use Control-C to stop this server and shut down all kernels (twice to skip confirmation).
[C 12:23:03.635 NotebookApp]
```

Continue reading the [User Guide](https://conda-incubator.github.io/conda-project/user_guide.html) to learn more.
