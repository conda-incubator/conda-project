# Control conda settings with a local .condarc file

Conda Project will look for a `.condarc` file in your project
directory to allow the project to alter the behavior of conda
specifically for the project.

In this example the solver is set to [`libmamba`](https://github.com/conda/conda-libmamba-solver).
You will need to have `conda-libmamba-solver` installed in your base environment.
