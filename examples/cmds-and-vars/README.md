# Defining commands and variables

The `conda-project.yml` file enables the definition of runable
commands and environment variables. In this example we will
define an environment variable with a default value and two
commands.

```yaml
# conda-project.yml
name: cmds-and-vars

environments:
  default:
    - environment.yml

variables:
  FOO: bar

commands:
  default:
    cmd: python -c 'import os;print(os.getenv("FOO"))'
    environment: default
  notdefault:
    cmd: python -c 'import os;print(os.getenv("FOO"))'
    environment: default
    variables:
      FOO: baz
```

Let's run the default command and you'll that FOO was set appropriately:

```text
❯ conda-project run default

Downloading and Extracting Packages


Downloading and Extracting Packages

Preparing transaction: done
Verifying transaction: done
Executing transaction: done
environment created at /Users/adefusco/Development/conda-incubator/conda-project/examples/cmds-and-vars/envs/default
bar
```

You'll see that the command named `notdefault` overrides the value of FOO:

```text
❯ conda-project run notdefault
baz
```

Environment variables are set when the environment is activated on Mac, Linux, and Windows.
Here I'm using a Mac and can run `printenv FOO` in the activated enviroment to print the value:

```text
❯ conda-project activate
## Project environment default activated in a new shell.
## Exit this shell to de-activate.
❯ conda activate /Users/adefusco/Development/conda-incubator/conda-project/examples/cmds-and-vars/envs/default
❯ printenv FOO
bar
```

Finally, can override the value of a defined variable through the use of a [`.env` file](https://saurabh-kumar.com/python-dotenv/#file-format).

```text
❯ echo "FOO=thud" > .env
❯ conda-project run default
thud
```

And it will always override the value in the `conda-project.yml` file even if override in the
command:

```text
❯ echo "FOO=thud" > .env
❯ conda-project run notdefault
thud
```
