# User Guide

## Initializing a new project

The purpose of `conda project init` is to provide a command like `conda create` that creates the
`environment.yml`, `conda-project.yml` and `conda-lock.default.yml` files before installing the
environment.
The `--install` flag can be used to build the files and then install the environment.

The init command will always write `channels` and `platforms` into the environment.yml file.

From within an existing project directory, run:

```shell
conda project init
```

Packages can also be specified when creating a project:

```shell
conda project init python=3.10
```

This will initialize your project with a new `conda-project.yml`, `environment.yml`, and local `.condarc` file.

### CLI help

The following is the output of `conda project init --help`:

```text
usage: conda-project init [-h] [--directory PROJECT_DIR] [-n NAME] [-c CHANNEL] [--platforms PLATFORMS] [--conda-configs CONDA_CONFIGS]
                            [--no-lock] [--install]
                            [dependencies [dependencies ...]]

Initialize a new project

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
  --no-lock             Do no create the conda-lock.<env>.yml file(s)
  --install             Create the local conda environment for the current platform.
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

`conda project install` enforces the use of `conda-lock`.
If a `conda-lock.<env>.yml` file is not present it will be created by install with the above
assumptions  if necessary.
If a `conda-lock.<env>.yml` file is found but the locked platforms do not match your current platform
it will raise an exception.

The live conda environment is built from a rendered lockfile (explicit type) for your current
platform, similar to how `conda lock install` works.

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

```
❯ conda project activate
CondaProjectError: The following variables do not have a default value and values
were not provided in the .env file or set on the command line when executing 'conda project run':
BAR
```

On Unix you can do the following

```
❯ BAR=set-on-cli conda project activate
## Project environment default activated in a new shell.
## Exit this shell to de-activate.
❯ conda activate /Users/adefusco/Development/conda-incubator/conda-project/examples/p/envs/default
```

On Windows in either `cmd.exe` you can use `set variable=value`

```
> set BAR=set-in-shell
> conda project activate
```

and finally, in Powershell you would use `$env`

```
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

```
> BAR=set-on-cli conda project run python vars.py
The value of FOO is has-default-value
The value of BAR is set-on-cli
The value of BAZ is None
```

On Linux, Mac, and Windows the return code of the `conda project run` is set to the
return code of the command it is executing. For example the above invocation returns
0, known as a successful execution. The `--version` flag, however exits with code 1, typically
meaning a failed execution.

```
> BAR=set-on-cli conda project run python vars.py --version
0.0.1
> echo $?
1
```

On Windows `cmd.exe` we can echo the `%ERRORLEVEL% variable.

```
> set BAR=set-on-cli
> conda project run python vars.py --version
> echo %ERRORLEVEL%
1
```

And in Powershell we print the `$LASTEXITCODE` variable

```
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

```
> BAR=set-on-cli conda project run
The value of FOO is has-default-value
The value of BAR is set-on-cli
The value of BAZ is None
```

Defined commands also support extra arguments, but the name of the command must be supplied.

```
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

```
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

To create a new project directory the `CondaProject.create()` method follows the CLI arguments
described above.
Projects are automatically locked.
See the docstring for `.create()` for more details.

```python
from conda_project import CondaProject

project = CondaProject.init(
   directory='new-project',
   dependencies=['python=3.8'],
)
```
