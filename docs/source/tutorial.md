# Tutorial

One of the main things that conda apart from other python packaging tool solutions is its ability to work with other languages and toolchains.  Conda
is happy to mix Python with packages from R, Java, C, etc. This tutorial explores using **conda-project** to create a [Shiny](https://shiny.rstudio.com/)
app using both **Jupyter notebook** on the Python side, and **shiny** on the R side.  After completing this tutorial, you will be able to:

 * Understand the relationship between conda-project commands and their corresponding actions.
 * Add a custom command to a project.
 * Use the `run` action to launch external processes.

If `conda-project` is not yet installed and started Project, follow the [Installation Instructions](index).

## Create a new project

This section of the tutorial explores the `init` and `activate` subcommands of conda-project.

1. Open a Command Prompt or terminal window.

2. Initialize the project in a new directory:
   ```shell
   conda-project init -n learn-cp --directory cp-tutorial --platform osx-arm64,linux-64 -c defaults -c conda-forge \
       python=3.10 notebook r-essentials r-plotly r-shiny
   ```

   At this point, **conda-project** will create a new directory, and write environment, lock, and project files to the new
   directory. This example passes the `osx-arm64` and `linux-64` platform architectures. This has the effect of speeding up
   the package resolution and lock file generation.  If the `--platform` argument is omitted, package resolution will be
   calculated across **conda-project**'s default list of platform architectures.

   ```{note}
   This tutorial issues the `init` action for a new project.  As noted in the [User Guide](user_guide), it is also possible
   to create a project from an existing environment file.

   If using windows, change the `--platform` argument to point to the correct architecture (win-64).
   ```

3. Navigate the newly created project directory:
   ```shell
   cd cp-tutorial
   ```

4. Investigate the contents of the newly created environment file:
   ```shell
   $ cat environment.yml
   channels:
     - defaults
     - conda-forge
   dependencies:
     - python=3.10
     - notebook
     - r-essentials
     - r-plotly
     - r-shiny
   platforms:
     - osx-arm64
     - linux-64
   ```

   ```{note}
   Refer to [conda-project create](user_guide) for a detailed list of options.
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

   Note that the `name` key is populated with the value supplied in the `init` action.

   An upcoming section of the tutorial will involve adding a custom command to the `commands` key. It's also
   possible to define variables using the `variables` key.  These key varlue pairs are loaded as overrides
   to the inherited execution environment when a `run` action is issued.

6. Initiate the `install` action on the project:
   ```shell
   $ conda-project install
   ```

   ```{note}
   As noted in a [preceding section](user_guide), the `install` action will initiate conda install
   for the active environment.
   ```

   ```{note}
   Running the install step is not strictly required. Calling the `run` command such as the one included
   in the next section, will result in `install` being called automatically.
   ```

## Create an example notebook-based shiny app

In this section of the tutorial, Jupyter notebook will be used to develop and refine the shiny app.

1. Use `conda-project` to launch Jupyer notebook.
   ```shell
   $ conda-project run jupyter notebook
   ```

2. Start a `R` kernel by clicking *New* and select the option labeled **R**.

3. Paste the following content into the first cell of the notebook and then run the cell.
   ```r
   library(shiny)
   library(data.table)
   library(ggplot2)

   ui <- fluidPage(
       titlePanel('Auto MPG'),
       sidebarPanel(
           radioButtons("origin", h3("Origin"),
                       choices = list("Asia" = "Asia"),
                       selected = "Asia")
       ),
       mainPanel(plotOutput(outputId = "distPlot"))
   )

   server <- function(input, output) {
       df = fread('http://bit.ly/autompg-csv')
       output$distPlot <- renderPlot({
           ggplot(data = df[origin==input$origin], mapping = aes(mpg)) + geom_density()
       })
   }

   shinyApp(ui = ui, server = server)
   ```

4. A link will appear at the bottom of the cell once the shiny app is being served.  Click the link and
   verify the output.

5. With the first cell selected, click the Stop button to stop the server.

6. Modify the content in the first cell by adding the US and Europe to the choices list in the UI:

   ```R
        choices = list("Asia" = "Asia", "Europe" = "Europe", "US" = "US"),
   ```

7. Run the cell again. When the server link appears, navigate to the shiny App and verify the code update is
   reflected in the UI.

8. Finally, save the verified R code to a file called `app.R` in the project directory.

```{note}
To exit the running Jupyter Notebook program press CTRL+C in the terminal or command line application.
```

## Add and run a project command

1. Register a new command to launch the [Shiny](https://shiny.rstudio.com/) app:

   Using a preferred editor, modify conda-project.yml by replacing the line `comands: {}` with the following:
   ```yaml
   commands:
     shiny: Rscript -e "shiny::runApp('.', port=8086, host='0.0.0.0')"
   ```

2. Use `conda-project` to run the newly added command using the `run` action:
   ```shell
   $ conda-project run shiny
   ```

   The application should now be running and available at http://localhost:8086/. To  close the running program,
   press CTRL+C in your terminal or command line.
