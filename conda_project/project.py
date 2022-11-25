# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import tempfile
import warnings
from collections import OrderedDict
from contextlib import nullcontext, redirect_stderr
from io import StringIO
from pathlib import Path
from subprocess import SubprocessError
from typing import List, Optional, Tuple, Union

from conda_lock.conda_lock import (
    default_virtual_package_repodata,
    make_lock_files,
    make_lock_spec,
    parse_conda_lock_file,
    render_lockfile_for_platform,
)
from conda_lock.vendor.conda.core.prefix_data import PrefixData
from pydantic import BaseModel, create_model

from .conda import CONDA_EXE, call_conda, current_platform
from .exceptions import CondaProjectError
from .project_file import (
    ENVIRONMENT_YAML_FILENAMES,
    PROJECT_YAML_FILENAMES,
    CondaProjectYaml,
    EnvironmentYaml,
    yaml,
)
from .utils import Spinner, env_variable, find_file

_TEMPFILE_DELETE = False if sys.platform.startswith("win") else True

DEFAULT_PLATFORMS = set(["osx-64", "win-64", "linux-64", current_platform()])

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.environ.get("CONDA_PROJECT_LOGLEVEL", "WARNING"))


class Environment(BaseModel):
    name: str
    sources: Tuple[Path, ...]
    prefix: Path
    lockfile: Path
    condarc: Path

    class Config:
        allow_mutation = False
        extra = "forbid"

    @property
    def _overrides(self):
        specified_channels = []
        specified_platforms = set()
        for fn in self.sources:
            env = EnvironmentYaml.parse_yaml(fn)
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

        return channel_overrides, platform_overrides

    @property
    def is_locked(self) -> bool:
        """
        bool: Returns True if the lockfile is consistent with the source files, False otherwise.
        """
        channel_overrides, platform_overrides = self._overrides
        if self.lockfile.exists():
            lock = parse_conda_lock_file(self.lockfile)
            spec = make_lock_spec(
                src_files=list(self.sources),
                channel_overrides=channel_overrides,
                platform_overrides=platform_overrides,
                virtual_package_repo=default_virtual_package_repodata(),
            )
            all_up_to_date = all(
                p in lock.metadata.platforms
                and spec.content_hash_for_platform(p) == lock.metadata.content_hash[p]
                for p in spec.platforms
            )
            return all_up_to_date
        else:
            return False

    @property
    def is_prepared(self) -> bool:
        """
        bool: Returns True if the Conda environment exists and is consistent with
              the environment source and lock files, False otherwise. If is_locked is
              False is_prepared is False.
        """
        if not (self.prefix / "conda-meta" / "history").exists():
            return False

        if not self.is_locked:
            return False

        # Generate a set of (name, version) tuples from the conda environment
        # TODO: Consider comparing more than the name & version
        # TODO: pip_interop_enabled is marked "DO NOT USE". What is the alternative?
        pd = PrefixData(self.prefix, pip_interop_enabled=True)
        installed_pkgs = {(p.name, p.version) for p in pd.iter_records()}

        # Generate a set of (name, version) tuples from the lockfile
        # We only include locked packages for the current platform, and don't
        # include optional dependencies (e.g. compile/build)
        lock = parse_conda_lock_file(self.lockfile)
        locked_pkgs = {
            (p.name, p.version)
            for p in lock.package
            if p.platform == current_platform() and not p.optional
        }

        # Compare the sets
        # We can do this because the tuples are hashable. Also we don't need to
        # consider ordering.
        return installed_pkgs == locked_pkgs

    def lock(
        self,
        force: bool = False,
        verbose: bool = False,
    ) -> None:
        """Generate locked package lists for the supplied or default platforms

        Utilizes conda-lock to build the .conda-lock.yml file.

        Args:
            force:       Rebuild the .conda-lock.yml file even if no changes were made
                         to the dependencies.
            verbose:     A verbose flag passed into the `conda lock` command.

        """
        if self.is_locked and not force:
            if verbose:
                print(
                    f"The lockfile {self.lockfile.name} already exists and is up-to-date.\n"
                    f"Run 'conda project lock --force {self.name} to recreate it from source specification."
                )
            return

        # Setup temporary file for conda-lock to write to.
        # If a package is removed from the environment source
        # after the lockfile has been created conda-lock updates
        # the hash in the lockfile but does not remove the unspecified
        # package (and necessary orphaned dependencies) from the lockfile.
        # To avoid this scenario lockfiles are written to a temporary location
        # and copied back to the self.lockfile path if successful.
        tempdir = Path(tempfile.mkdtemp())
        lockfile = tempdir / self.lockfile.name

        channel_overrides, platform_overrides = self._overrides

        specified_channels = []
        for fn in self.sources:
            env = EnvironmentYaml.parse_yaml(fn)
            for channel in env.channels or []:
                if channel not in specified_channels:
                    specified_channels.append(channel)

        with redirect_stderr(StringIO()) as _:
            with env_variable("CONDARC", str(self.condarc)):
                if verbose:
                    context = Spinner(prefix=f"Locking dependencies for {self.name}")
                else:
                    context = nullcontext()

                with context:
                    try:
                        make_lock_files(
                            conda=CONDA_EXE,
                            src_files=list(self.sources),
                            lockfile_path=lockfile,
                            kinds=["lock"],
                            platform_overrides=platform_overrides,
                            channel_overrides=channel_overrides,
                        )
                        shutil.copy(lockfile, self.lockfile)
                    except SubprocessError as e:
                        output = json.loads(e.output)
                        msg = output["message"].replace(
                            "target environment",
                            f"supplied channels: {channel_overrides or specified_channels}",
                        )
                        msg = "Project failed to lock\n" + msg
                        raise CondaProjectError(msg)
                    finally:
                        shutil.rmtree(tempdir)

        lock = parse_conda_lock_file(self.lockfile)
        msg = f"Locked dependencies for {', '.join(lock.metadata.platforms)} platforms"
        logger.info(msg)

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
        if not self.is_locked:
            if verbose and self.lockfile.exists():
                print(f"The lockfile {self.lockfile} is out-of-date, re-locking...")
            self.lock(verbose=verbose)

        if self.is_prepared:
            if not force:
                logger.info(f"environment already exists at {self.prefix}")
                if verbose:
                    print(
                        f"The environment already exists and is up-to-date.\n"
                        f"run 'conda project prepare --force {self.name} to recreate it from the locked dependencies."
                    )
                return self.prefix
        elif (self.prefix / "conda-meta" / "history").exists() and not self.is_prepared:
            if not force:
                if verbose:
                    print(
                        f"The environment exists but does not match the locked dependencies.\n"
                        f"Run 'conda project prepare --force {self.name}' to recreate the environment from the "
                        f"locked dependencies."
                    )
                return self.prefix

        lock = parse_conda_lock_file(self.lockfile)
        if current_platform() not in lock.metadata.platforms:
            msg = (
                f"Your current platform, {current_platform()}, is not in the supported locked platforms.\n"
                f"You may need to edit your environment source files and run 'conda project lock' again."
            )
            raise CondaProjectError(msg)

        rendered = render_lockfile_for_platform(
            lockfile=lock,
            platform=current_platform(),
            kind="explicit",
            include_dev_dependencies=False,
            extras=None,
        )

        _pip_dependency_prefix = "# pip "  # from conda-lock
        pip_requirements = [
            line.split(_pip_dependency_prefix)[1].replace("#md5=None", "")
            for line in rendered
            if line.startswith(_pip_dependency_prefix)
        ]

        with tempfile.NamedTemporaryFile(mode="w", delete=_TEMPFILE_DELETE) as f:
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

        if pip_requirements:
            with tempfile.NamedTemporaryFile(mode="w", delete=_TEMPFILE_DELETE) as f:
                f.write("\n".join(pip_requirements))
                f.flush()
                args = [
                    "run",
                    *("-p", str(self.prefix)),
                    *("pip", "install", "--no-deps"),
                    *("-r", str(f.name)),
                ]
                call_conda(
                    args, condarc_path=self.condarc, verbose=verbose, logger=logger
                )

        with (self.prefix / ".gitignore").open("wt") as f:
            f.write("*")

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
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

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

        self.project_yaml_path = find_file(self.directory, PROJECT_YAML_FILENAMES)
        if self.project_yaml_path is not None:
            self._project_file = CondaProjectYaml.parse_yaml(self.project_yaml_path)
        else:
            options = " or ".join(PROJECT_YAML_FILENAMES)
            logger.info(
                f"No {options} file was found. Checking for environment YAML files."
            )

            environment_yaml_path = find_file(
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

        existing_project_file = find_file(directory, PROJECT_YAML_FILENAMES)
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

        condarc = {}
        for config in conda_configs or []:
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

    def check(self, verbose=False) -> bool:
        """Check the project for inconsistencies or errors.

        This will check that .conda-lock.yml files exist for each environment
        and that they are up-to-date against the environment specification.

        Returns:
            Boolean: True if all environments are locked and update to date,
                     False if any environment is not locked or out-of-date.

        """
        return_status = []

        for env in self.environments.values():
            if not env.lockfile.exists():
                if verbose:
                    print(f"The environment {env.name} is not locked.", file=sys.stderr)
                    print(
                        f"Run 'conda project lock {env.name}' to create.",
                        file=sys.stderr,
                    )
                return_status.append(False)
            elif not env.is_locked:
                if verbose:
                    print(
                        f"The lockfile for environment {env.name} is out-of-date.",
                        file=sys.stderr,
                    )
                    print(
                        f"Run 'conda project lock {env.name}' to fix.", file=sys.stderr
                    )
                return_status.append(False)
            else:
                return_status.append(True)

        return all(return_status)
