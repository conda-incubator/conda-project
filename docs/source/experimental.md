# Experimental Features

As new capability is being developed for Conda Project we will release features with the label *Experimental*, meaning
that their behavior may change rapidly while we gather feedback from users. Please
[submit a ticket](https://github.com/conda-incubator/conda-project/issues/new/choose) to have your voice heard.

## Extract a project archive

*New in version 0.2.0*

The Conda Project CLI commands `lock`, `check`, `install`, `activate`, `run` are capable of extracting a project
archive, in formats like `.zip`, `.tar.gz`, `.tar.bz2`, and others supported by
[libarchive](https://www.libarchive.org/). The archive file can either be on the local filesystem or provided as
a [fsspec](https://filesystem-spec.readthedocs.io/en/latest/?badge=latest)-compatible URI. Note that you may need
separately install driver packages to download the archive from remote systems like S3, Github, Google Cloud Storage,
Azure, and others. See [FSSpec github organization repositories](https://github.com/orgs/fsspec/repositories) for
more information. To pass specific parameters to the FSSpec driver use the `--archive-storage-options` flag.

```text
  --project-archive PROJECT_ARCHIVE_FILE_OR_URL
                        EXPERIMENTAL: Extract and run directly from a project archive. The archive can be a local file or a fsspec compatible URL.
                        You may need to install appropriate driver packages to work with remote archives. Optionally, use --directory to set the
                        destination directory of the extracted project.
  --archive-storage-options ARCHIVE_STORAGE_OPTIONS
                        EXPERIMENTAL: Comma separated list of fsspec storage_options for accessing a remote archive For example --archive-storage-
                        options username=<user>,password=<pass>
```

Here's an example of running a project directly from an archive stored on S3. Note that `s3fs` may not already be
installed with Conda Project. This will run the default command for the
[cmds-and-vars](https://github.com/conda-incubator/conda-project/tree/main/examples/cmds-and-vars) example project.

First the archive is downloaded and the contents are extracted to a local directory called `cmds-and-vars`. You
can change the output directory with the optional `--directory` flag. Then the `run` action is performed, in
this case on the default command. You'll see that it installs the local locked environment and executes the command.

```text
❯ conda install -c conda-forge conda-project s3fs
❯ conda-project run --project-archive s3://conda-projects/cmds-and-vars.tar.gz --archive-storage-options anon=True
cmds-and-vars/.condarc
cmds-and-vars/README.md
cmds-and-vars/conda-lock.default.yml
cmds-and-vars/conda-project.yml
cmds-and-vars/environment.yml

Downloading and Extracting Packages


Downloading and Extracting Packages

Preparing transaction: done
Verifying transaction: done
Executing transaction: done
environment created at /Users/adefusco/Desktop/cmds-and-vars/envs/default
bar
```

## Run a command with an external environment

*New in version 0.2.0*

There are times when it may be desirable to execute a defined or ad-hoc command on an environment that is not managed
by Conda Project. The `--external-environment` flag will accept a named environment or the path to the environment
prefix.

```text
  --external-environment ENV_NAME_OR_PREFIX
                        EXPERIMENTAL: Specify the name or prefix path to a conda environment not declared in this project.
```

As of now you will still need to define an `environment:` in the conda-project.yml file, but it can be empty.

```yaml
name: test-command

environments: {}

variables:
  FOO: 'bar'

commands:
  default:
    cmd: python -c 'import os,sys;foo=os.getenv("FOO");print(f"FOO is {foo}\nPython executable {sys.executable}")'
```

For example the default command in this project can be executed using my `base` environment.

```text
❯ conda-project run --external-environment base
FOO is bar
Python executable /Users/adefusco/Applications/miniconda3/bin/python
```
