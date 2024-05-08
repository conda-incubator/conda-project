# User Guide

## Initializing a new project

The purpose of `conda project init` is to provide a command like `conda create` that creates the
`environment.yml`, `conda-project.yml` and `conda-lock.default.yml` files before installing the
environment.
The `--install` flag can be used to build the files and then install the environment.

The init command will always write `channels` and `platforms` into the environment.yml file.

From within an existing project directory, run:

```text
conda project init
```

Packages can also be specified when creating a project:

```text
conda project init python=3.10
```

To specify pip dependencies on initialization, use the `@pip::` prefix:

```text
conda project init python=3.10 @pip::numpy
```

This will initialize your project with a new `conda-project.yml`, `environment.yml`, and local `.condarc` file.

### CLI help

The following is the output of `conda project init --help`:

```text
usage: conda-project init [-h] [--directory PROJECT_DIR] [-n NAME] [-c CHANNEL] [--platforms PLATFORMS]
                          [--conda-configs CONDA_CONFIGS] [--lock] [--install] [--from-environment FROM_ENVIRONMENT]
                          [PACKAGE_SPECIFICATION ...]

Initialize a new project

positional arguments:
  PACKAGE_SPECIFICATION
                        Packages to add to the environment.yml. The format for each package is '<name>[<op><version>]'
                        where <op> can be =, <, >, <=, or >=.

options:
  -h, --help            show this help message and exit
  --directory PROJECT_DIR
                        Project directory (defaults to current directory)
  -n NAME, --name NAME  Name for the project.
  -c CHANNEL, --channel CHANNEL
                        Additional channel to search for packages. The default channel is 'defaults'. Multiple channels are
                        added with repeated use of this argument.
  --platforms PLATFORMS
                        Comma separated list of platforms for which to lock dependencies. The default is osx-64,osx-
                        arm64,linux-64,win-64
  --conda-configs CONDA_CONFIGS
                        Comma separated list of conda configuration parameters to write into the .condarc file in the
                        project directory. The format for each config is key=value. For example --conda-configs
                        experimental_solver=libmamba,channel_priority=strict
  --lock                Create the conda-lock.<env>.yml file(s)
  --install             Create the local conda environment for the current platform.
  --from-environment FROM_ENVIRONMENT
                        Initialize the default environment spec and lock from an existing conda environment by name or
                        prefix.
```

### If I already have an `environment.yml`

If the user writes a minimal `environment.yml` file as shown below, `conda-project` will make two
assumptions:

1. all packages come from the `defaults` channel, and
1. the dependencies will be locked for `win-64, linux-64, mac-64` and your current platform if
   it is not one of those three.

### If I already have an installed environment

The `--from-environment <name-or-prefix>` argument can be used to bootstrap a Conda Project from an existing
conda environment. This procedure will perform the following steps

1. Read the existing environment and construct the `environment.yml` file pinning versions for only the requested
   packages.
1. Construct the `conda-lock.<env-name>.yml` file for the current platform listing *all* of the packages in the
   environment as they are now.
    * Only packages for the current platform are listed in the lock file to save time. You may also use the `--lock`
      flag to additionally lock the remaining platforms according to the `environment.yml` file generated in the
      previous step.

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

variables: {}
commands: {}
```

```{note}
Environment YAML files are specified as relative to the location of the `conda-project.yml` file.
Each key in `environments:` can be utilized in `conda project lock <env-name>` or
 `conda project install <env-name>`.
 These commands also accept `--all` to lock and prepare each of the defined environments.
```

If no env name is supplied lock, prepare, and clean assume the *default environment* is the
first  environment listed in the `conda-project.yml` file.

## Locking dependencies

conda-project uses
[conda-lock](https://github.com/conda-incubator/conda-lock) to lock environment dependencies.
To manually lock your environments, run:

```text
conda project lock
```

Locking of dependencies completely ignores the user's channel settings in `~/.condarc` and will
only use channels supplied by the `environment.yml` file.

`conda project lock` utilizes  the `--check-input-hash` feature of `conda-lock`.
When you run `conda project lock` multiple times, the lock file will only be updated if the
`environment.yml` has changed.
To force a re-lock use `conda project lock --force`.

## Installing your environments

`conda project install` enforces the use of `conda-lock`.
If a `conda-lock.<env>.yml` file is not present it will be created by install with the above
assumptions  if necessary.
If a `conda-lock.<env>.yml` file is found but the locked platforms do not match your current platform
it will raise an exception.

The live conda environment is built from a rendered lockfile (explicit type) for your current
platform, similar to how `conda lock install` works.

## Adding packages to an environment

The `conda project add` command works similar to `conda install` to add packages. Like `init` you
can specify pip packages with the `@pip::` prefix.
The `add` command will re-lock and install your environment each time it is run.

For example:

```text
conda project init
conda project add -c defaults python=3.10
conda project add conda-forge::pandas requests @pip::pydantic
conda project add "pandas<2"
```

Note that in the above commands `pandas` was added twice. Adding a package that already exists in your
environment.yml file will replace that entry with the new one.

To add packages to an environment other than the first one in the conda-project.yml file use the `--environment <name>`
flag.

Here's the full help for the `add` command.

```text
usage: conda-project add [-h] [--directory PROJECT_DIR] [--project-archive PROJECT_ARCHIVE_FILE_OR_URL]
                         [--archive-storage-options ARCHIVE_STORAGE_OPTIONS] [--environment ENVIRONMENT] [-c CHANNEL]
                         [PACKAGE_SPECIFICATION [PACKAGE_SPECIFICATION ...]]

Add packages to an environment

positional arguments:
  PACKAGE_SPECIFICATION
                        Packages to add to the environment.yml. The format for each package is '[<prefix>::]<name>[<op><version>]'
                        where <op> can be =, <, >, <=, or >=.Most commonly `<prefix>::` declares the conda channel from which to
                        install packages. Use the prefix `@pip::` to add pip package dependencies with support for full pip package
                        specification syntax.

optional arguments:
  -h, --help            show this help message and exit
  --directory PROJECT_DIR
                        Project directory (defaults to current directory)
  --project-archive PROJECT_ARCHIVE_FILE_OR_URL
                        EXPERIMENTAL: Extract and run directly from a project archive. The archive can be a local file or a fsspec
                        compatible URL. You may need to install appropriate driver packages to work with remote archives. Optionally,
                        use --directory to set the destination directory of the extracted project.
  --archive-storage-options ARCHIVE_STORAGE_OPTIONS
                        EXPERIMENTAL: Comma separated list of fsspec storage_options for accessing a remote archive For example
                        --archive-storage-options username=<user>,password=<pass>
  --environment ENVIRONMENT
  -c CHANNEL, --channel CHANNEL
                        Additional channel to search for packages. The default channel is 'defaults'. Multiple channels are added with
                        repeated use of this argument.
```

## Removing a package from an environment

The inverse of `add` is `conda project remove`. Removing a package will also re-lock and re-install the environment.
Only the name of the package is required to remove it and you can remove a pip package with the `@pip::` prefix.

Start from where we left of in the previous section we initialized the project and added packages.

```text
conda project init
conda project add -c defaults python=3.10
conda project add "conda-forge::pandas<2" requests @pip::pydantic
```

In the end our environment.yml now looks like:

```yaml
name:
channels:
  - defaults
dependencies:
  - python=3.10
    - conda-forge::pandas<2
    - requests
    - pip
    - pip:
      - pydantic
variables:
prefix:
platforms:
  - osx-arm64
  - linux-64
  - osx-64
  - win-64
```

To remove packages we need only specify the name of package

```text
conda project remove pandas @pip::pydantic
```

Then we are left with:

```yaml
name:
channels:
  - defaults
dependencies:
  - python=3.10
  - requests
  - pip
  - pip: []
variables:
prefix:
platforms:
  - osx-arm64
  - linux-64
  - osx-64
  - win-64
```

Here's the help output for the `remove` command:

```text
usage: conda-project remove [-h] [--directory PROJECT_DIR]
                            [--project-archive PROJECT_ARCHIVE_FILE_OR_URL]
                            [--archive-storage-options ARCHIVE_STORAGE_OPTIONS]
                            [--environment ENVIRONMENT]
                            [PACKAGE_SPECIFICATION [PACKAGE_SPECIFICATION ...]]

Remove packages to an environment

positional arguments:
  PACKAGE_SPECIFICATION
                        Packages to remove from the environment.yml. Only the
                        name of the package is required here. To remove a pip
                        package use the pypyi:: prefix.

optional arguments:
  -h, --help            show this help message and exit
  --directory PROJECT_DIR
                        Project directory (defaults to current directory)
  --project-archive PROJECT_ARCHIVE_FILE_OR_URL
                        EXPERIMENTAL: Extract and run directly from a project
                        archive. The archive can be a local file or a fsspec
                        compatible URL. You may need to install appropriate
                        driver packages to work with remote archives.
                        Optionally, use --directory to set the destination
                        directory of the extracted project.
  --archive-storage-options ARCHIVE_STORAGE_OPTIONS
                        EXPERIMENTAL: Comma separated list of fsspec
                        storage_options for accessing a remote archive For
                        example --archive-storage-options
                        username=<user>,password=<pass>
  --environment ENVIRONMENT
```

## Activating environments in the shell

`conda project activate [environment]` will launch a shell and activate the named conda environment.
If no environment name is supplied the first environment is activated. The `activate` command will
force updating the lock and install the environment if it has not already been completed. Unlike
`conda activate`, which is capable of adjusting your current shell process, `conda project activate`
starts a new shell so it preferable to exit the shell back to the parent rather than running `conda deactivate`.

## Minimal example

```text
❯ conda project init python=3.8
Locking dependencies for default: done
Locked dependencies for win-64, osx-64, osx-arm64, linux-64 platforms
Project created at /Users/adefusco/Development/conda-incubator/conda-project/examples/new-project

❯ tree -a ./
./
├── .condarc
├── conda-project.yml
├── conda-lock.default.yml
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
variables: {}
commands: {}
```

## Environment variables

Conda Project supports defining environment variables in the `conda-project.yml` file that will
be set upon environment activation or when running commands. Variables are defined in the
`variables:` key and can have an optional default value. Starting from the minimal example above
I'll add a variable `FOO` with the default value `has-default-value` and the variable `BAR` with
no default value.

```yaml
name: new-project
environments:
  default:
    - environment.yml

variables:
  FOO: has-default-value
  BAR:

commands: {}
```

The values of the variables can be set or overridden by the use of a `.env` file (see the
[python-dotenv documentation](https://saurabh-kumar.com/python-dotenv/#file-format) for more details) or
by setting the variable in your shell.

In this example the `BAR` environment variable is unset so `conda project activate` will not start
unless a value is provided by the shell or in a `.env` file.

```text
❯ conda project activate
CondaProjectError: The following variables do not have a default value and values
were not provided in the .env file or set on the command line when executing 'conda project run':
BAR
```

On Unix you can do the following

```text
❯ BAR=set-on-cli conda project activate
## Project environment default activated in a new shell.
## Exit this shell to de-activate.
❯ conda activate /Users/adefusco/Development/conda-incubator/conda-project/examples/p/envs/default
```

On Windows in either `cmd.exe` you can use `set variable=value`

  ```text
> set BAR=set-in-shell
> conda project activate
```

and finally, in Powershell you would use `$env`

```text
> $env:BAR = 'set-in-shell'
> conda project activate
```

## Defining and running commands

Conda Project supports running commands as if the desired environment were activated, similar
to [conda run](https://docs.conda.io/projects/conda/en/latest/commands/run.html).

In Conda Project the `run` command can be used to execute ad-hoc commands or those defined
in the `conda-project.yml` file. Note that `conda project run` should not be utilized after
`conda project activate`. The `run` command will not work from within an activated environment.

Let's start with a simple python script called `vars.py`, that prints environment variables
and optionally takes an argument `--version` to also print the Python version.

```python
import os
import sys

if len(sys.argv) > 1 and sys.argv[1] == '--version':
    print("0.0.1")
    sys.exit(1)
else:
    print(f"The value of FOO is {os.environ.get('FOO')}")
    print(f"The value of BAR is {os.environ.get('BAR')}")
    print(f"The value of BAZ is {os.environ.get('BAZ')}")
```

Note that when the `--version` flag is provided the return code for this script is 1, meaning
a failure.

We can execute this script with the `default` environment as an ad-hoc command using the Python
interpreter provided by the default environment. Here a `.env` file is utilized to provide the
value of the BAR variable.

```text
> BAR=set-on-cli conda project run python vars.py
The value of FOO is has-default-value
The value of BAR is set-on-cli
The value of BAZ is None
```

On Linux, Mac, and Windows the return code of the `conda project run` is set to the
return code of the command it is executing. For example the above invocation returns
0, known as a successful execution. The `--version` flag, however exits with code 1, typically
meaning a failed execution.

```text
> BAR=set-on-cli conda project run python vars.py --version
0.0.1
> echo $?
1
```

On Windows `cmd.exe` we can echo the `%ERRORLEVEL% variable.

```text
> set BAR=set-on-cli
> conda project run python vars.py --version
> echo %ERRORLEVEL%
1
```

And in Powershell we print the `$LASTEXITCODE` variable

```text
> $env:BAR = 'set-on-cli'
> conda project run python vars.py --version
0.0.1
> $LASTEXITCODE
1
```

Defined commands in the conda-project.yml are placed under the `commands:` key. Commands
written in one line are set to execute over the default (first) environment.

```yaml
commands:
  print-vars: python vars.py
```

Now you can use `conda project run` without arguments and it will execute the first
named command in the `conda-project.yml` file.

```text
> BAR=set-on-cli conda project run
The value of FOO is has-default-value
The value of BAR is set-on-cli
The value of BAZ is None
```

Defined commands also support extra arguments, but the name of the command must be supplied.

```text
> BAR=set-on-cli conda project run print-vars --version
0.0.1
```

Here is an example of a full specified named command that declares the environment
from which it will run, and variables. Command variables can override project-level variables
or define new variables. Note that even though command-level-variables override project-level
variables the final value of the variable can still be override by the `.env` file and that
can be overridden by the shell.

```yaml
commands:
  print-vars:
    cmd: python vars.py
    environment: default
    variables:
      BAR: set-in-cmd
      BAZ: a-new-var
```

Here the command is run by name without any extra variables. This is the same as
`conda project run`

```text
> conda project run print-vars
The value of FOO is bar
The value of BAR is set-on-cli
The value of BAZ is a-new-var
```

## Python API

The Python API provides full support for the above workflows by creating a `CondaProject` object.
`CondaProject` takes a single optional argument to supply the path to the project.
The default value is the current working directory, `.` Every CondaProject has at least one
conda environment.

A project directory containing only an `environment.yml` file will create a single environment
of the name `default`, which can be locked or installed.
If multiple environments are defined in a `conda-project.yml` the `.environments` attribute
provides dictionary-style syntax for each named environment.
The first defined conda environment in the `conda-project.yml` is accessible as
`project.default_environment`

```python
from conda_project import CondaProject

project = CondaProject()
project.default_environment.lock()
prefix = project.default_environment.install()

## alternative, use the name 'default'

project.environments['default'].lock()
prefix = project.environments['default'].install()
```

To create a new project directory the `CondaProject.init()` method follows the CLI arguments
described above.
Projects are automatically locked.
See the docstring for `.init()` for more details.

```python
from conda_project import CondaProject

project = CondaProject.init(
   directory='new-project',
   dependencies=['python=3.8'],
)
```
