# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging
import os
import tempfile
from contextlib import nullcontext, redirect_stderr
from pathlib import Path
from sys import platform
from typing import List, Optional

import ruamel.yaml as yaml
from conda_lock.conda_lock import (make_lock_files, parse_conda_lock_file,
                                   render_lockfile_for_platform)

from .conda import CONDA_EXE, call_conda, current_platform
from .exceptions import CondaProjectError
from .utils import Spinner, env_variable

ENVIRONMENT_YAML_FILENAMES = ("environment.yml", "environment.yaml")
DEFAULT_PLATFORMS = set(['osx-64', 'win-64', 'linux-64', current_platform()])


class CondaProject:
    """A project managed by `conda-project`.

    Attributes:
        directory: The project base directory. Defaults to the current working directory.
        condarc: A path to the local `.condarc` file. Defaults to `<directory>/.condarc`.
        environment_file: A path to the environment file.
        lock_file: A path to the conda-lock file.
        logger: The logger for project

    Args:
        directory: The project base directory.

    Raises:
        CondaProjectError: If no suitable environment file is found.

    """

    def __init__(self, directory: Path | str = "."):
        self.logger = logging.getLogger('conda_project.CondaProject')
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        self.logger.handlers.clear()
        self.logger.addHandler(handler)
        self.logger.setLevel(os.environ.get('CONDA_PROJECT_LOGLEVEL', 'WARNING'))
        self.logger.propagate = False

        self.directory = Path(directory).resolve()
        self.logger.info(f'created Project instance at {self.directory}')

        self.condarc = self.directory / ".condarc"
        self.environment_file = self._find_environment_file()
        self.lock_file = self.environment_file.parent / 'conda-lock.yml'

    def _find_environment_file(self) -> Path:
        """Find an environment file in the project directory.

        Raises:
            CondaProjectError: If no suitable environment file can be found.

        """
        for filename in ENVIRONMENT_YAML_FILENAMES:
            path = self.directory / filename
            if path.exists():
                self.logger.info(f'found environment file {path}')
                return path
        raise CondaProjectError(
            f"No Conda environment.yml or environment.yaml file was found in {self.directory}."
        )

    @property
    def default_env(self) -> Path:
        """A path to the default conda environment."""
        return self.directory / "envs" / "default"

    @classmethod
    def create(cls,
               directory: Path | str = '.',
               name: Optional[str] = None,
               dependencies: Optional[List[str]] = None,
               channels: Optional[List[str]] = None,
               platforms: Optional[List[str]] = None,
               conda_configs: Optional[List[str]] = None,
               lock_dependencies: bool = True,
               verbose: bool = False) -> CondaProject:
        """Create a new project

        Creates the environment.yml file from the specified dependencies,
        channels, and platforms. Further a local .condarc can also be
        created in the directory.

        Args:
            directory:         The path to use as the project directory. The directory
                               will be created if it doesn't exist.
            name:              Name of the project. The default is the basename of the project
                               directory.
            dependencies:      List of package dependencies to include in the environment.yml in
                               MatchSpec format.
            channels:          List of channels to search for dependencies. The default value is
                               ['defaults']
            platforms:         List of platforms over which to lock the dependencies. The default is
                               osx-64, linux-64, win-64 and your current platform if it is not already
                               included.
            conda_configs:     List of Conda configuration parameters to include in the .condarc file
                               written to the project directory.
            lock_dependencies: Create the conda-lock.yml file for the requested dependencies.
                               Default is True.

        Returns:
            CondaProject instance for the project directory.

        """

        directory = Path(directory).resolve()
        if not directory.exists():
            directory.mkdir(parents=True)

        if name is None:
            name = directory.name

        environment_yaml = {}
        environment_yaml['name'] = name
        environment_yaml['channels'] = channels or ['defaults']
        environment_yaml['dependencies'] = dependencies or []
        environment_yaml['platforms'] = platforms or list(DEFAULT_PLATFORMS)

        with open(directory / 'environment.yml', 'wt') as f:
            yaml.round_trip_dump(environment_yaml, f,
                                 default_flow_style=False, block_seq_indent=2, indent=2)

        if conda_configs is not None:
            condarc = {}
            for config in conda_configs:
                k, v = config.split('=')
                condarc[k] = v

            with open(directory / '.condarc', 'wt') as f:
                yaml.round_trip_dump(condarc, f,
                                     default_flow_style=False, block_seq_indent=2, indent=2)

        project = CondaProject(directory)

        if lock_dependencies:
            project.lock(verbose=verbose)

        if verbose:
            print(f'Project created at {directory}')

        return project

    def lock(self, force: bool = False, verbose: bool = False) -> None:
        """Generate locked package lists for the supplied or default platforms

        Utilizes conda-lock to build the conda-lock.yml file.

        Args:
            force: Rebuild the conda-lock.yml file even if no changes were made
            verbose: A verbose flag passed into the `conda lock` command.

        """
        with open(self.environment_file) as f:
            env = yaml.safe_load(f)

        channel_overrides = None
        if 'channels' not in env:
            self.logger.warning(f"there is no 'channels:' key in {self.environment_file.name} assuming 'defaults'.")
            channel_overrides = ["defaults"]

        platform_overrides = None
        if 'platforms' not in env:
            platform_overrides = list(DEFAULT_PLATFORMS)

        platforms = env.get('platforms', []) or platform_overrides
        self.logger.info(f'locking dependencies for {",".join(platforms)}')
        self.logger.info(f'requested dependencies {env.get("dependencies", [])}')

        devnull = open(os.devnull, 'w')
        with redirect_stderr(devnull):
            with env_variable('CONDARC', str(self.condarc)):
                if verbose:
                    context = Spinner(prefix='Locking dependencies')
                else:
                    context = nullcontext()

                with context:
                    make_lock_files(
                        conda=CONDA_EXE,
                        src_files=[self.environment_file],
                        lockfile_path=self.lock_file,
                        check_input_hash=not force,
                        kinds=['lock'],
                        platform_overrides=platform_overrides,
                        channel_overrides=channel_overrides
                    )

        lock = parse_conda_lock_file(self.lock_file)
        msg = (f"Locked requested dependencies {' '.join(env['dependencies'])}\n"
               f"for {', '.join(lock.metadata.platforms)} platforms")
        self.logger.info(msg)
        if verbose:
            print(msg)

    def prepare(self, force: bool = False, verbose: bool = False) -> Path:
        """Prepare the default conda environment.

        Creates a new conda environment and installs the packages from the environment.yaml file.
        Environments are always created from the conda-lock.yml file. The conda-lock.yml
        will be created if it does not already exist.

        Args:
            force: If True, will force creation of a new conda environment.
            verbose: A verbose flag passed into the `conda create` command.

        Returns:
            A path to the created environment.

        """
        default_env = self.default_env
        conda_meta = default_env / "conda-meta" / "history"
        if conda_meta.exists() and not force:
            self.logger.info(f'environment already exists at {default_env}')
            if verbose:
                print('The environment already exists, use --force to recreate it from the locked dependencies.')
            return default_env

        if not self.lock_file.exists():
            self.lock(verbose=verbose)

        lock = parse_conda_lock_file(self.lock_file)
        if current_platform() not in lock.metadata.platforms:
            msg = (f'Your current platform, {current_platform()}, is not in the supported locked platforms.\n'
                   f'You may need to edit your {self.environment_file.name} file and run conda project lock again.')
            raise CondaProjectError(msg)

        rendered = render_lockfile_for_platform(
            lockfile=lock,
            platform=current_platform(),
            kind='explicit',
            include_dev_dependencies=False, extras=None
        )

        delete = False if platform.startswith('win') else True
        with tempfile.NamedTemporaryFile(mode='w', delete=delete) as f:
            f.write('\n'.join(rendered))
            f.flush()

            args = [
                "create",
                "-y",
                *("--file", f.name),
                *("-p", str(default_env)),
            ]
            if force:
                args.append("--force")

            _ = call_conda(
                args,
                condarc_path=self.condarc,
                verbose=verbose,
                logger=self.logger
            )

        msg = f'environment created at {default_env}'
        self.logger.info(msg)
        if verbose:
            print(msg)

        return default_env

    def clean(self, verbose: bool = False) -> None:
        """Remove the default conda environment."""
        _ = call_conda(
            ["env", "remove", "-p", str(self.default_env)],
            condarc_path=self.condarc,
            verbose=verbose,
            logger=self.logger
        )
