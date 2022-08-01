# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging
import os
import tempfile
import warnings
from collections import OrderedDict
from contextlib import nullcontext, redirect_stderr
from pathlib import Path
from pydantic import BaseModel, create_model
from sys import platform
from typing import List, Optional, Union, Tuple

from conda_lock.conda_lock import (
    make_lock_files,
    parse_conda_lock_file,
    render_lockfile_for_platform,
)

from .conda import CONDA_EXE, call_conda, current_platform
from .exceptions import CondaProjectError
from .project_file import (
    PROJECT_YAML_FILENAMES,
    ENVIRONMENT_YAML_FILENAMES,
    CondaProjectYaml,
    EnvironmentYaml,
    yaml,
)
from .utils import Spinner, env_variable

DEFAULT_PLATFORMS = set(["osx-64", "win-64", "linux-64", current_platform()])

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.environ.get("CONDA_PROJECT_LOGLEVEL", "WARNING"))


def _find_file(directory: Path, options: tuple) -> Optional[Path]:
    """Search for a file in directory or its parents from a tuple of filenames.

    Returns:
        The path to the file if found else None

    """
    for filename in options:
        path = directory / filename
        if path.exists():
            return path.resolve()
    return None


class Environment(BaseModel):
    name: str
    sources: Tuple[Path, ...]
    prefix: Path
    lockfile: Path
    condarc: Path

    class Config:
        allow_mutation = False

    @property
    def is_prepared(self) -> bool:
        return (self.prefix / "conda-meta" / "history").exists()

    @property
    def is_locked(self) -> bool:
        return self.lockfile.exists()

    def lock(
        self,
        force: bool = False,
        verbose: bool = False,
    ) -> None:
        """Generate locked package lists for the supplied or default platforms

        Utilizes conda-lock to build the conda-lock.yml file.

        Args:
            force:       Rebuild the .conda-lock.yml file even if no changes were made
                         to the dependencies.
            verbose:     A verbose flag passed into the `conda lock` command.

        """
        specified_channels = []
        specified_platforms = set()
        for fn in self.sources:
            env = EnvironmentYaml.parse_yaml(fn)
            # env.channels = [] if env.channels is None else env.channels
            for channel in env.channels or []:
                if channel not in specified_channels:
                    specified_channels.append(channel)
            if env.platforms is not None:
                specified_platforms.update(env.platforms)

        channel_overrides = None
        if not specified_channels:
            env_files = ",".join([source.name for source in self.sources])
            msg = f"there are no 'channels:' key in {env_files} assuming 'defaults'."
            warnings.warn(msg)
            channel_overrides = ["defaults"]

        platform_overrides = None
        if not specified_platforms:
            platform_overrides = list(DEFAULT_PLATFORMS)

        # platforms = specified_platforms or platform_overrides
        # self.logger.info(f'locking dependencies for {",".join(platforms)}')
        # self.logger.info(f'requested dependencies {env.get("dependencies", [])}')

        devnull = open(os.devnull, "w")
        with redirect_stderr(devnull):
            with env_variable("CONDARC", str(self.condarc)):
                if verbose:
                    context = Spinner(prefix=f"Locking dependencies for {self.name}")
                else:
                    context = nullcontext()

                with context:
                    make_lock_files(
                        conda=CONDA_EXE,
                        src_files=self.sources,
                        lockfile_path=self.lockfile,
                        check_input_hash=not force,
                        kinds=["lock"],
                        platform_overrides=platform_overrides,
                        channel_overrides=channel_overrides,
                    )

        lock = parse_conda_lock_file(self.lockfile)
        msg = f"Locked dependencies for {', '.join(lock.metadata.platforms)} platforms"
        logger.info(msg)
        if verbose:
            print(msg)

    def prepare(
        self,
        force: bool = False,
        verbose: bool = False,
    ) -> Path:
        """Prepare the conda environment.

        Creates a new conda environment and installs the packages from the environment.yaml file.
        Environments are always created from the conda-lock.yml file. The conda-lock.yml
        will be created if it does not already exist.

        Args:
            force: If True, will force creation of a new conda environment.
            verbose: A verbose flag passed into the `conda create` command.

        Raises:
            CondaProjectError: If no suitable environment file can be found.

        Returns:
            The path to the created environment.

        """
        conda_meta = self.prefix / "conda-meta" / "history"
        if conda_meta.exists() and not force:
            logger.info(f"environment already exists at {self.prefix}")
            if verbose:
                print(
                    "The environment already exists, use --force to recreate it from the locked dependencies."
                )
            return self.prefix

        if not self.lockfile.exists():
            self.lock(verbose=verbose)

        lock = parse_conda_lock_file(self.lockfile)
        if current_platform() not in lock.metadata.platforms:
            msg = (
                f"Your current platform, {current_platform()}, is not in the supported locked platforms.\n"
                f"You may need to edit your environment files and run conda project lock again."
            )
            raise CondaProjectError(msg)

        rendered = render_lockfile_for_platform(
            lockfile=lock,
            platform=current_platform(),
            kind="explicit",
            include_dev_dependencies=False,
            extras=None,
        )

        delete = False if platform.startswith("win") else True
        with tempfile.NamedTemporaryFile(mode="w", delete=delete) as f:
            f.write("\n".join(rendered))
            f.flush()

            args = [
                "create",
                "-y",
                *("--file", f.name),
                *("-p", str(self.prefix)),
            ]
            if force:
                args.append("--force")

            _ = call_conda(
                args, condarc_path=self.condarc, verbose=verbose, logger=logger
            )

        msg = f"environment created at {self.prefix}"
        logger.info(msg)
        if verbose:
            print(msg)

        return self.prefix

    def clean(
        self,
        verbose: bool = False,
    ) -> None:
        """Remove the conda environment."""

        _ = call_conda(
            ["env", "remove", "-p", str(self.prefix)],
            condarc_path=self.condarc,
            verbose=verbose,
            logger=logger,
        )


class BaseEnvironments(BaseModel):
    def __getitem__(self, key: str) -> Environment:
        return getattr(self, key)

    def keys(self):
        return self.__fields__.keys()

    class Config:
        allow_mutation = False


class CondaProject:
    """A project managed by `conda-project`.

    Attributes:
        directory: The project base directory. Defaults to the current working directory.
        condarc: A path to the local `.condarc` file. Defaults to `<directory>/.condarc`.
        environment_file: A path to the environment file.
        lock_file: A path to the conda-lock file.

    Args:
        directory: The project base directory.

    Raises:
        CondaProjectError: If no suitable environment file is found.

    """

    def __init__(self, directory: Union[Path, str] = "."):
        self.directory = Path(directory).resolve()
        logger.info(f"created Project instance at {self.directory}")

        self.project_yaml_path = _find_file(self.directory, PROJECT_YAML_FILENAMES)
        if self.project_yaml_path is not None:
            self._project_file = CondaProjectYaml.parse_yaml(self.project_yaml_path)
        else:
            options = " or ".join(PROJECT_YAML_FILENAMES)
            logger.info(
                f"No {options} file was found. Checking for environment YAML files."
            )

            environment_yaml_path = _find_file(
                self.directory, ENVIRONMENT_YAML_FILENAMES
            )
            if environment_yaml_path is None:
                options = " or ".join(ENVIRONMENT_YAML_FILENAMES)
                raise CondaProjectError(f"No Conda {options} file was found.")

            self._project_file = CondaProjectYaml(
                name=self.directory.name,
                environments=OrderedDict(
                    [("default", [environment_yaml_path.relative_to(self.directory)])]
                ),
            )

        self.condarc = self.directory / ".condarc"

    @classmethod
    def create(
        cls,
        directory: Union[Path, str] = ".",
        name: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        channels: Optional[List[str]] = None,
        platforms: Optional[List[str]] = None,
        conda_configs: Optional[List[str]] = None,
        lock_dependencies: bool = True,
        verbose: bool = False,
    ) -> CondaProject:
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
            force:             Force creation of project and environment files if they already
                               exist. The default value is False.
            verbose:           Print information to stdout. The default value is False.

        Returns:
            CondaProject instance for the project directory.

        """

        directory = Path(directory).resolve()
        if not directory.exists():
            directory.mkdir(parents=True)

        existing_project_file = _find_file(directory, PROJECT_YAML_FILENAMES)
        if existing_project_file is not None:
            if verbose:
                print(f"Existing project file found at {existing_project_file}.")
            return cls(directory)

        if name is None:
            name = directory.name

        environment_yaml = EnvironmentYaml(
            channels=channels or ["defaults"],
            dependencies=dependencies or [],
            platforms=platforms or list(DEFAULT_PLATFORMS),
        )

        environment_yaml_path = directory / "environment.yml"
        environment_yaml.yaml(directory / "environment.yml")

        project_yaml = CondaProjectYaml(
            name=name,
            environments=OrderedDict(
                [("default", [environment_yaml_path.relative_to(directory)])]
            ),
        )

        project_yaml.yaml(directory / "conda-project.yml")

        if conda_configs is not None:
            condarc = {}
            for config in conda_configs:
                k, v = config.split("=")
                condarc[k] = v
            yaml.dump(condarc, directory / ".condarc")

        project = cls(directory)

        if lock_dependencies:
            project.default_environment.lock(verbose=verbose)

        if verbose:
            print(f"Project created at {directory}")

        return project

    @property
    def environments(self) -> BaseEnvironments:
        envs = OrderedDict()
        for env_name, sources in self._project_file.environments.items():
            envs[env_name] = Environment(
                name=env_name,
                sources=[self.directory / str(s) for s in sources],
                prefix=self.directory / "envs" / env_name,
                lockfile=self.directory / f"{env_name}.conda-lock.yml",
                condarc=self.condarc,
            )
        Environments = create_model(
            "Environments",
            **{k: (Environment, ...) for k in envs},
            __base__=BaseEnvironments,
        )
        return Environments(**envs)

    @property
    def default_environment(self) -> Environment:
        name = next(iter(self._project_file.environments))
        return self.environments[name]
