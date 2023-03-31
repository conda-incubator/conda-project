# Project with only an environment.yml file

This project contains just an environment.yml file.
You can use the command `conda project activate` from within
this directory, which will lock depedencies to a file called
`conda-lock.default.yml`, install the environment into a local
prefix called `./envs/default` and activate it in a new shell.

In the text block below you'll see that the python executable path
in the activate env belongs to the local environment.

```text
❯ conda-project activate
/Users/adefusco/Development/conda-incubator/conda-project/conda_project/project.py:352: UserWarning: there are no 'channels:' key in environment.yml assuming 'defaults'.
  warnings.warn(msg)
Locking dependencies for environment default on platforms win-64, osx-64, linux-64, osx-arm64: done

Downloading and Extracting Packages


Downloading and Extracting Packages

Preparing transaction: done
Verifying transaction: done
Executing transaction: done
environment created at /Users/adefusco/Development/conda-incubator/conda-project/examples/env-file-only/envs/default
## Project environment default activated in a new shell.
## Exit this shell to de-activate.
❯ conda activate /Users/adefusco/Development/conda-incubator/conda-project/examples/env-file-only/envs/default
❯ python -c 'import sys;print(sys.executable)'
/Users/adefusco/Development/conda-incubator/conda-project/examples/env-file-only/envs/default/bin/python
```
