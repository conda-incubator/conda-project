# Tutorial

This tutorial explores using conda project to create a [Panel](https://panel.holoviz.org) app.
After completing this tutorial, you will be able to:

 * Understand the relationship between conda-project commands and their corresponding actions.
 * Add a custom command to a project.
 * Use the `run` action to launch external processes.

If `conda-project` is not yet installed and started Project, follow the [Installation Instructions](index).

## Create a new project

This section of the tutorial explores the `create` and `activate` subcommands of conda-project.

1. Open a Command Prompt or terminal window.

2. Initialize the project in a new directory:
   ```shell
   $ conda-project -n learn-cp --directory cp-tutorial python=3.10 notebook hvplot panel xarray pooch netCDF4
   ```

   ```{note}
   This tutorial issues the `create` action for a new project.  As noted in the [User Guide](user_guide), it is also possible
   to create a project from an existing environment file.
   ```

3. Navigate the newly created project directory:
   ```shell
   $ cd cp-tutorial
   ```

4. Investigate the contents of the newly created environment file:
   ```shell
   $ cat environment.yml
   name:
   channels:
     - defaults
   dependencies:
     - python=3.10
     - notebook
     - hvplot
     - panel
     - xarray
     - pooch
     - netCDF4
   variables:
   prefix:
   platforms:
     - osx-64
     - linux-64
     - osx-arm64
     - win-64
   ```

   ```{note}
   It's possible to stipulate additional environment information, such as `channels` and
   `platforms` in the create command.  Refer to [conda-project create](user_guide) for a detailed list of options.
   ```

5. Investigate the contents of the newly created conda project file:
   ```yaml
   $ cat conda-project.yml
   name: learn-cp
     environments:
   default:
     - environment.yml
   variables: {}
   commands: {}
   ```

   Note that the `name` key is populated with the value supplied in the `create` action.

   An upcoming section of the tutorial will involve adding a custom command to the `commands` key. It's also
   possible to define variables using the `variables` key.  These key varlue pairs are loaded as overrides
   to the inherited execution environment when a `run` action is issued.

6. Activate the projects' default environment by calling the `activate` action:
   ```shell
   $ anaconda-project activate
   ```

7. Initiate the `prepare` action on the project:
   ```shell
   $ conda-project prepare
   ```

   ```{note}
   As noted in a [preceding section](user_guide), the `prepare` action will initiate conda install
   for the active environment.
   ```

## Create an example notebook-based Panel app

In this section, first create a new notebook called ``Interactive.ipynb`` by using one of the following methods:

 * Download this [quickstart](https://raw.githubusercontent.com/Anaconda-Platform/anaconda-project/master/examples/quickstart/Interactive.ipynb) example:

   * Right-click the link and "*Save As*", naming the file ``Interactive.ipynb`` and saving it into your new *cp-tutorial* folder, or

   * Use the ``curl`` command below. *This can be used on a unix-like platform.*
     ```shell
     $ curl https://raw.githubusercontent.com/Anaconda-Platform/anaconda-project/master/examples/quickstart/Interactive.ipynb -o Interactive.ipynb
     ```

     ```{note}
     This example is taken from a larger, more full-featured [hvPlot interactive](https://raw.githubusercontent.com/holoviz/hvplot/master/examples/user_guide/Interactive.ipynb).
     The larger example will also work in this tutorial.
     ```

 * Alternatively, a Jupyter notebook session can be launched using the following shell command:

   ```shell
   $ conda-project run jupyter notebook
   ```

   Click the New button and choose the Python3 option. Paste the following contents into a cell and click File|Save as..., naming the file ``Interactive``.

     ```python
     import xarray as xr, hvplot.xarray, hvplot.pandas, panel as pn, panel.widgets as pnw

     ds     = xr.tutorial.load_dataset('air_temperature')
     diff   = ds.air.interactive.sel(time=pnw.DiscreteSlider) - ds.air.mean('time')
     kind   = pnw.Select(options=['contourf', 'contour', 'image'], value='image')
     plot   = diff.hvplot(cmap='RdBu_r', clim=(-20, 20), kind=kind)

     hvlogo = pn.panel("https://hvplot.holoviz.org/assets/hvplot-wm.png", width=100)
     pnlogo = pn.panel("https://panel.holoviz.org/_static/logo_stacked.png", width=100)
     text   = pn.panel("## Select a time and type of plot", width=400)

     pn.Column(
         pn.Row(hvlogo, pn.Spacer(width=20), pn.Column(text, plot.widgets()), pnlogo),
         plot.panel()).servable()
     ```

  To exit the running Jupyter Notebook program press CTRL+C in the terminal or command line application.


## Add and run a project command

1. Register a new command to launch the notebook as a [Panel](https://panel.holoviz.org) app:

   Using a preferred editor, modify conda-project.yml by replacing the line `comands: {}` with the following:
   ```yaml
   commands:
     panel: panel serve Interactive.ipynb
   ```

2. Run the newly added command using the `run` action:
   ```shell
   $ anaconda-project run panel
   ```

   The application should now be running and available at http://localhost:5006/Interactive. To  close the running program,
   press CTRL+C in your terminal or command line.
