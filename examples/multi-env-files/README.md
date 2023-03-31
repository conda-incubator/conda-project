# Multiple environment files

By using a `conda-project.yml` specification file you can
define multiple conda environments each one built from one
or more discrete environment YAML files.

```yaml
# conda-project.yml
name: mutli-env-files

environments:
  default:
    - environment.yml
  test:
    - environment.yml
    - extras.yml
```

The `test` environment is defined as a [compound specification](https://github.com/conda/conda-lock#compound-specification) when locked.

You'll see that this project contains fives files (apart from README.md).
Each defined environment has a [conda-lock file](https://github.com/conda/conda-lock).

```text
❯ tree ./
./
├── README.md
├── conda-lock.default.yml
├── conda-lock.test.yml
├── conda-project.yml
├── environment.yml
├── extras.yml
├── print_version.py
└── test_get_version.py

```

To execute the Python script and the test script you can use `conda project run` over
the appropriate environment. On first run of `conda project run` the conda-lock file is
rendered for your current platform and installed in the `./envs/<env-name>` directory.

```text
❯ conda-project run --environment default python print_version.py

Downloading and Extracting Packages


Downloading and Extracting Packages

Preparing transaction: done
Verifying transaction: done
Executing transaction: done
environment created at /Users/adefusco/Development/conda-incubator/conda-project/examples/multi-env-files/envs/default
Python version 3.10.10
```

```text
❯ conda project run --environment test pytest test_get_version.py

Downloading and Extracting Packages


Downloading and Extracting Packages

Preparing transaction: done
Verifying transaction: done
Executing transaction: done
environment created at /Users/adefusco/Development/conda-incubator/conda-project/examples/multi-env-files/envs/test
========================================================== test session starts ==========================================================
platform darwin -- Python 3.10.10, pytest-7.1.2, pluggy-1.0.0 -- /Users/adefusco/Development/conda-incubator/conda-project/examples/multi-env-files/envs/test/bin/python
cachedir: .pytest_cache
rootdir: /Users/adefusco/Development/conda-incubator/conda-project, configfile: setup.cfg
collected 1 item

test_get_version.py::test_get_version PASSED                                                                                      [100%]

========================================================= slowest 20 durations ==========================================================
0.00s setup    examples/multi-env-files/test_get_version.py::test_get_version
0.00s call     examples/multi-env-files/test_get_version.py::test_get_version
0.00s teardown examples/multi-env-files/test_get_version.py::test_get_version
=========================================================== 1 passed in 0.00s ===========================================================
```
