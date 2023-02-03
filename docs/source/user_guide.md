# User Guide

## Creating a new project

The purpose of `conda project create` is to provide a command like `conda create` that creates the
`environment.yml`, `conda-project.yml` and `default.conda-lock.yml` files before installing the
environment.
The `--prepare` flag can be used to build the files and then install the environment.

The create command will always write `channels` and `platforms` into the environment.yml file.

From within an existing project directory, run:

```shell
conda project create
```

Packages can also be specified when creating a project:

```shell
conda project create python=3.10
```

This will initialize your project with a new `conda-project.yml`, `environment.yml`, and local `.condarc` file.

### CLI help

The following is the output of `conda project create --help`:

```
usage: conda-project create [-h] [--directory PROJECT_DIR] [-n NAME] [-c CHANNEL] [--platforms PLATFORMS] [--conda-configs CONDA_CONFIGS]
                            [--no-lock] [--prepare]
                            [dependencies [dependencies ...]]

Create a new project

positional arguments:
  dependencies          Packages to add to the environment.yml in MatchSpec format.

optional arguments:
  -h, --help            show this help message and exit
  --directory PROJECT_DIR
                        Project directory (defaults to current directory)
  -n NAME, --name NAME  Name for the project.
  -c CHANNEL, --channel CHANNEL
                        Additional channel to search for packages. The default channel is 'defaults'. Multiple channels are added with repeated
                        use of this argument.
  --platforms PLATFORMS
                        Comma separated list of platforms for which to lock dependencies. The default is win-64,linux-64,osx-64,osx-arm64
  --conda-configs CONDA_CONFIGS
                        Comma separated list of conda configuration parameters to write into the .condarc file in the project directory. The
                        format for each config is key=value. For example --conda-configs experimental_solver=libmamba,channel_priority=strict
  --no-lock             Do no create the conda-lock.yml file
  --prepare             Create the local conda environment for the current platform.
```


### If I already have an `environment.yml`

If the user writes a minimal `environment.yml` file as shown below, `conda-project` will make two
assumptions:
1. all packages come from the `defaults` channel, and
1. the dependencies will be locked for `win-64, linux-64, mac-64` and your current platform if
   it is not one of those three.

## The conda-project.yml file

An optional `conda-project.yml` file is defined that supports multiple conda environments per
project and each environment can be built from multiple `conda` environment YAML sources, which
uses
[conda-lock compound specification](https://github.com/conda-incubator/conda-lock#compound-specification).

For example:

```yaml
name: project-name

environments:
  main:
    - environment.yml
  development:
    - environment.yml
    - ../dev-extras.yml
```

```{note}
Environment YAML files are specified as relative to the location of the `conda-project.yml` file.
Each key in `environments:` can be utilized in `conda project lock <env-name>` or
 `conda project prepare <env-name>`.
 These commands also accept `--all` to lock and prepare each of the defined environments.
```

If no env name is supplied lock, prepare, and clean assume the *default environment* is the
first  environment listed in the `conda-project.yml` file.

## Locking dependencies

conda-project uses
[conda-lock](https://github.com/conda-incubator/conda-lock) to lock environment dependencies.
To manually lock your environments, run:

```shell
conda project lock
```

Locking of dependencies completely ignores the user's channel settings in `~/.condarc` and will
only use channels supplied by the `environment.yml` file.

`conda project lock` utilizes  the `--check-input-hash` feature of `conda-lock`.
When you run `conda project lock` multiple times, the lock file will only be updated if the
`environment.yml` has changed.
To force a re-lock use `conda project lock --force`.

## Preparing your environments
`conda project prepare` enforces the use of `conda-lock`.
If a `.conda-lock.yml` file is not present it will be created by prepare with the above
assumptions  if necessary.
If a `.conda-lock.yml` file is found but the locked platforms do not match your current platform
it will raise an exception.

The live conda environment is built from a rendered lockfile (explicit type) for your current
platform, similar to how `conda lock install` works.

## Minimal full example

```
❯ conda project create python=3.8
Locking dependencies for default: done
Locked dependencies for win-64, osx-64, osx-arm64, linux-64 platforms
Project created at /Users/adefusco/Development/conda-incubator/conda-project/examples/new-project

❯ tree -a ./
./
├── .condarc
├── conda-project.yml
├── default.conda-lock.yml
└── environment.yml

❯ cat environment.yml
name: new-project
channels:
  - defaults
dependencies:
  - python=3.8
platforms:
  - win-64
  - osx-64
  - osx-arm64
  - linux-64

❯ cat conda-project.yml
name: new-project
environments:
  default:
    - environment.yml
```

## Python API

The Python API provides full support for the above workflows by creating a `CondaProject` object.
`CondaProject` takes a single optional argument to supply the path to the project.
The default value is the current working directory, `.` Every CondaProject has at least one
conda  environment.

A project directory containing only an `environment.yml` file will create a single environment
of the name `default`, which can be locked or prepared.
If multiple environments are defined in a `conda-project.yml` the `.environments` attribute
provides dictionary-style syntax for each named environment.
The first defined conda environment in the `conda-project.yml` is accessible as
`project.default_environment`

```python
from conda_project import CondaProject

project = CondaProject()
project.default_environment.lock()
prefix = project.default_environment.prepare()

## alternative, use the name 'default'

project.environments['default'].lock()
prefix = project.environments['default'].prepare()
```

To create a new project directory the `CondaProject.create()` method follows the CLI arguments
described above.
Projects are automatically locked.
See the docstring for `.create()` for more details.

```python
from conda_project import CondaProject

project = CondaProject.create(
  directory='new-project',
  dependencies=['python=3.8'],
)
```
