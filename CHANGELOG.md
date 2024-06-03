# Changelog

## [0.4.2] - 2024-06-03

- Fix default_platforms by @AlbertDeFusco in [#168](https://github.com/conda-incubator/conda-project/pull/168)

## [0.4.1] - 2024-05-04

- Fixing pypi trigger by @AlbertDeFusco in [#165](https://github.com/conda-incubator/conda-project/pull/165)
- On push tags by @AlbertDeFusco in [#166](https://github.com/conda-incubator/conda-project/pull/166)

## [0.4.0] - 2024-05-03

### Added

- Make it possible to override project environments location by @jkong-anaconda in [#159](https://github.com/conda-incubator/conda-project/pull/159)
- Handle relative paths and writing nonexistent directories for CONDA_PROJECT_ENVS_PATH by @jkong-anaconda in [#161](https://github.com/conda-incubator/conda-project/pull/161)
- [feat] initialize from an existing environment by @AlbertDeFusco in in [#162](https://github.com/conda-incubator/conda-project/pull/162)
- Expand vars in envs_path by @AlbertDeFusco in [#164](https://github.com/conda-incubator/conda-project/pull/164)

### Maintenance

- [chore] test py3.12 and newer conda by @AlbertDeFusco in [#163](https://github.com/conda-incubator/conda-project/pull/163)
- revise the badges by @AlbertDeFusco in [#155](https://github.com/conda-incubator/conda-project/pull/155)
- [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in [#154](https://github.com/conda-incubator/conda-project/pull/154)

### New Contributors

- @jkong-anaconda made their first contribution in [#159](https://github.com/conda-incubator/conda-project/pull/159)

## [0.3.2] - 2024-02-09

### Fixes

- Depend on setuptools [#152](https://github.com/conda-incubator/conda-project/pull/152)

## [0.3.1] - 2024-02-08

### Fixes

- Allow conda-project to be installed alongside Pydantic 2 [#146](https://github.com/conda-incubator/conda-project/pull/146)

## [0.3.0] - 2023-01-30

### Added

- `add` and `remove` pip or conda packages from environments [#112](https://github.com/conda-incubator/conda-project/pull/112)

### Fixes

- Fix issues where environments re-lock [#140](https://github.com/conda-incubator/conda-project/pull/140)

### Maintenance

- Update pre-commit [#139](https://github.com/conda-incubator/conda-project/pull/139)
- Update docs to conda-sphinx-theme [#143](https://github.com/conda-incubator/conda-project/pull/143)

## [0.2.1] - 2023-08-01

### Fixes

- Fix expand `~` in paths [#110](https://github.com/conda-incubator/conda-project/pull/110)
- Fix relative paths in `conda-lock.<env>.yml` [#125](https://github.com/conda-incubator/conda-project/pull/125)
- Fix support for newer conda-lock versions [#129](https://github.com/conda-incubator/conda-project/pull/129)
- Fix for inconsistent installed envs [#135](https://github.com/conda-incubator/conda-project/pull/135)
- Fix for error messages from conda [#134](https://github.com/conda-incubator/conda-project/pull/134)
- Fix locking platforms message [#137](https://github.com/conda-incubator/conda-project/pull/137)

### Maintenance

- Add new static badge linking to documentation [#116](https://github.com/conda-incubator/conda-project/pull/116)

## [0.2.0] - 2023-04-24

### Added

- Experimental: run commands using an external conda environment. [#106](https://github.com/conda-incubator/conda-project/pull/106)
- Experimental: download and extract a project archive on first use. [#106](https://github.com/conda-incubator/conda-project/pull/106)
- Experimental: Anaconda Project -> Conda Project conversion script. [#106](https://github.com/conda-incubator/conda-project/pull/106)

## [0.1.1] - 2023-04-05

### Maintenance

- Build system and CI fixes [#96](https://github.com/conda-incubator/conda-project/pull/96), [#97](https://github.com/conda-incubator/conda-project/pull/97), [#100](https://github.com/conda-incubator/conda-project/pull/100), [#101](https://github.com/conda-incubator/conda-project/pull/101)

## [0.1.0] - 2023-03-31

### Added

- Automatic dependency locking
- Multi-environment support
- Environment activation
- Running commands defined in the `conda-project.yml` file and ad-hoc commands
- Defined environment variables with `.env` support for commands and environment activation
- Tested on Mac, Linux, and Windows
