# Configuration

## Environment Variables

You can modify Conda Project configuration settings using these environment variables.

### CONDA_PROJECT_ENVS_PATH

This variable provides a list of directories to the path where conda environments
will be created for this project. The format is identical to a standard `PATH` variable on the host
operating system---a list of directories separated by `:` on Unix systems and `;` on Windows---except
that empty entries are permitted. The paths are interpreted as follows:

- If the path is aboslute, it used as-is
- If a path is relative, it is interpreted relative to the root directory
  of the project itself (`PROJECT_DIR`). For example, a path entry
  `envs` is interpreted as

  - `$PROJECT_DIR/envs` (Unix)
  - `%PROJECT_DIR%\envs` (Windows)

- When searching for a path to created an environment for the project, the directories are searched in
  left-to-right order.
- The first writeable directory will be used to create the environment

The default behavior of Cond Project is 

`CONDA_PROJECT_ENVS_PATH=envs`

For example, given a Unix machine with

`CONDA_PROJECT_ENVS_PATH=/opt/envs:envs2:/home/user/conda/envs`

Then Conda Project will create an environment named `default`
in the first writeable of the following locations:

- `/opt/envs/default`
- `$PROJECT_DIR/envs2/default`
- `/home/user/conda/envs/default`
