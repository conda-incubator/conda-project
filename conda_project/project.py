# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sys
import tempfile
import warnings
import weakref
from collections import OrderedDict
from contextlib import nullcontext, redirect_stderr
from io import StringIO
from pathlib import Path
from subprocess import SubprocessError
from typing import Dict, List, NoReturn, Optional, Tuple, Union

from conda_lock._vendor.conda.core.prefix_data import PrefixData
from conda_lock._vendor.conda.models.records import PackageType
from conda_lock.conda_lock import (
    default_virtual_package_repodata,
    make_lock_files,
    make_lock_spec,
    parse_conda_lock_file,
    render_lockfile_for_platform,
)
from pydantic import BaseModel, create_model

from .conda import CONDA_EXE, call_conda, conda_activate, conda_run, current_platform
from .exceptions import CommandNotFoundError, CondaProjectError, CondaProjectLockFailed
from .project_file import (
    ENVIRONMENT_YAML_FILENAMES,
    PROJECT_YAML_FILENAMES,
    CondaProjectYaml,
    EnvironmentYaml,
    yaml,
)
from .utils import Spinner, env_variable, find_file, prepare_variables

_TEMPFILE_DELETE = False if sys.platform.startswith("win") else True

DEFAULT_PLATFORMS = set(["osx-64", "win-64", "linux-64", current_platform()])

# A regex pattern used to extract package name and hash from output of "pip freeze"
_PIP_FREEZE_REGEX_PATTERN = re.compile(r"(?P<name>[\w-]+) @ .*sha256=(?P<sha256>\w+)")

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.environ.get("CONDA_PROJECT_LOGLEVEL", "WARNING"))


def _package_type_to_manager(package_type: PackageType) -> str:
    """Convert a package type to its associated manager, either "conda" or "pip"."""
    if package_type in PackageType.conda_package_types():
        return "conda"
    return "pip"


def _load_pip_sha256_hashes(prefix: str) -> dict[str, str]:
    """Load the sha256 hashes of pip-managed packages via pip freeze.

    Returns:
        A dictionary mapping the package name to its sha256 hash.

    """
    try:
        pip_freeze = call_conda(["run", "-p", prefix, "pip", "freeze"])
    except CondaProjectError as e:  # pragma: no cover
        if ("pip: command not found" in str(e)) or (
            "'pip' is not recognized" in str(e)
        ):
            return {}
        else:
            raise e

    pip_sha256: dict[str, str] = {}
    for line in pip_freeze.stdout.strip().splitlines():
        m = _PIP_FREEZE_REGEX_PATTERN.match(line)
        if m is not None:
            pip_sha256[m.group("name")] = m.group("sha256")
    return pip_sha256


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
                raise CondaProjectError(f"No conda {options} file was found.")

            self._project_file = CondaProjectYaml(
                name=self.directory.name,
                environments=OrderedDict(
                    [("default", [environment_yaml_path.relative_to(self.directory)])]
                ),
            )

        self.condarc = self.directory / ".condarc"

    @classmethod
    def init(
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
        """Initialize a new project.

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
            conda_configs:     List of conda configuration parameters to include in the .condarc file
                               written to the project directory.
            lock_dependencies: Create the conda-lock.<env>.yml file(s) for the requested dependencies.
                               Default is True.
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
                sources=tuple([self.directory / str(s) for s in sources]),
                prefix=self.directory / "envs" / env_name,
                lockfile=self.directory / f"conda-lock.{env_name}.yml",
                project=weakref.proxy(self),
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

    @property
    def commands(self) -> BaseCommands:
        cmds = OrderedDict()
        for name, cmd in self._project_file.commands.items():
            if isinstance(cmd, str):
                cmd_args = cmd
                environment = self.default_environment
                command_variables = None
            else:
                cmd_args = cmd.cmd
                environment = (
                    self.environments[cmd.environment]
                    if cmd.environment is not None
                    else self.default_environment
                )
                command_variables = cmd.variables

            cmds[name] = Command(
                name=name,
                cmd=cmd_args,
                environment=environment,
                command_variables=command_variables,
                project=weakref.proxy(self),
            )
        Commands = create_model(
            "Commands", **{k: (Command, ...) for k in cmds}, __base__=BaseCommands
        )
        return Commands(**cmds)

    @property
    def default_command(self) -> Command:
        if not self._project_file.commands:
            raise CommandNotFoundError("This project has no defined commands.")

        name = next(iter(self._project_file.commands))
        return self.commands[name]

    def check(self, verbose=False) -> bool:
        """Check the project for inconsistencies or errors.

        This will check that conda-lock.<env>.yml file(s) exist for each environment
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


class Variable(BaseModel):
    key: str
    default_value: str


class Environment(BaseModel):
    name: str
    sources: Tuple[Path, ...]
    prefix: Path
    lockfile: Path
    project: CondaProject

    class Config:
        allow_mutation = False
        extra = "forbid"
        arbitrary_types_allowed = True

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
    def is_consistent(self) -> bool:
        """
        bool: Returns True if the conda environment exists and is consistent with
              the environment source and lock files, False otherwise. If is_locked is
              False is_prepared is False.
        """
        if not (self.prefix / "conda-meta" / "history").exists():
            return False

        if not self.is_locked:
            return False

        # Here, we ensure that we clear the cache on the PrefixData class. This is to
        # ensure that we freshly load the installed packages each time.
        PrefixData._cache_.pop(self.prefix, None)

        pip_sha256 = _load_pip_sha256_hashes(str(self.prefix))

        # Generate a set of (name, version, manager, sha256) tuples from the conda environment
        # We also convert the conda package_type attribute to a string in the set
        # {"conda", "pip"} to allow direct comparison with conda-lock.
        # TODO: pip_interop_enabled is marked "DO NOT USE". What is the alternative?
        pd = PrefixData(self.prefix, pip_interop_enabled=True)
        installed_pkgs = set()
        for p in pd.iter_records():
            manager = _package_type_to_manager(p.package_type)
            if manager == "pip":
                sha256 = pip_sha256.get(p.name)
            else:
                sha256 = p.sha256

            installed_pkgs.add((p.name, p.version, manager, sha256))

        # Generate a set of (name, version, manager, sha256) tuples from the lockfile
        # We only include locked packages for the current platform, and don't
        # include optional dependencies (e.g. compile/build)
        lock = parse_conda_lock_file(self.lockfile)
        locked_pkgs = {
            (p.name, p.version, p.manager, p.hash.sha256)
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

        Utilizes conda-lock to build the conda-lock.<env>.yml file(s).

        Args:
            force:       Rebuild the conda-lock.<env>.yml file even if no changes were made
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
            with env_variable("CONDARC", str(self.project.condarc)):
                if verbose:
                    p = (
                        platform_overrides
                        if platform_overrides is not None
                        else DEFAULT_PLATFORMS
                    )
                    context = Spinner(
                        prefix=f"Locking dependencies for environment {self.name} on "
                        f"platforms {', '.join(p)}"
                    )
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
                        try:
                            output = json.loads(e.output)
                        except json.decoder.JSONDecodeError:
                            # A bug in conda-libmamba-solver causes # serialization
                            # errors so we'll just print the full stack trace on error.
                            raise CondaProjectLockFailed(e.stderr)

                        msg = output["message"].replace(
                            "target environment",
                            f"supplied channels: {channel_overrides or specified_channels}",
                        )
                        msg = "Project failed to lock\n" + msg
                        raise CondaProjectLockFailed(msg)
                    finally:
                        shutil.rmtree(tempdir)

        lock = parse_conda_lock_file(self.lockfile)
        msg = f"Locked dependencies for {', '.join(lock.metadata.platforms)} platforms"
        logger.info(msg)

    def install(
        self,
        force: bool = False,
        as_platform: Optional[str] = None,
        verbose: bool = False,
    ) -> Path:
        """Install all dependencies into the conda environment.

        Creates a new conda environment and installs the packages from the environment.yaml file.
        Environments are always created from the conda-lock.<env>.yml file(s). The conda-lock.<env>.yml file(s)
        will be created if they do not already exist.

        Args:
            force: If True, will force creation of a new conda environment.
            as_platform: Install dependencies as an explicit platform. By default, the
                platform will be identified for the system.
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

        if self.is_consistent:
            if not force:
                logger.info(f"environment already exists at {self.prefix}")
                if verbose:
                    print(
                        f"The environment already exists and is up-to-date.\n"
                        f"run 'conda project prepare --force {self.name} to recreate it from the locked dependencies."
                    )
                return self.prefix
        elif (
            self.prefix / "conda-meta" / "history"
        ).exists() and not self.is_consistent:
            if not force:
                if verbose:
                    print(
                        f"The environment exists but does not match the locked dependencies.\n"
                        f"Run 'conda project prepare --force {self.name}' to recreate the environment from the "
                        f"locked dependencies."
                    )
                return self.prefix

        lock = parse_conda_lock_file(self.lockfile)

        local_env_condarc = self.prefix / "condarc"

        previous_platform = None
        if local_env_condarc.exists():
            with local_env_condarc.open("r") as f:
                previous_platform = yaml.load(f).get("subdir", None)

        platform = current_platform()
        if as_platform is None:
            if previous_platform is not None:
                platform = previous_platform
        else:
            platform = as_platform

        if platform not in lock.metadata.platforms:
            msg = (
                f"Your current platform, {platform}, is not in the supported locked platforms.\n"
                f"You may need to edit your environment source files and run 'conda project lock' again.\n"
                f"If your system supports multiple platforms you can try using the --as-platform <subdir> flag."
            )
            raise CondaProjectError(msg)

        rendered = render_lockfile_for_platform(
            lockfile=lock,
            platform=platform,
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

            variables = {}
            if as_platform is not None:
                variables["CONDA_SUBDIR"] = as_platform

            args = [
                "create",
                "-y",
                *("--file", f.name),
                *("-p", str(self.prefix)),
            ]
            if force:
                args.append("--force")

            _ = call_conda(
                args,
                condarc_path=self.project.condarc,
                variables=variables,
                verbose=verbose,
                logger=logger,
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
                    args,
                    condarc_path=self.project.condarc,
                    verbose=verbose,
                    logger=logger,
                )

        with (self.prefix / ".gitignore").open("wt") as f:
            f.write("*")

        if platform != current_platform():
            with (self.prefix / "condarc").open("wt") as f:
                f.write(f"subdir: {platform}\n")

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
            condarc_path=self.project.condarc,
            verbose=verbose,
            logger=logger,
        )

    def activate(self, verbose=False) -> None:
        if not self.is_consistent:
            self.install(verbose=verbose)

        env = prepare_variables(
            self.project.directory, self.project._project_file.variables
        )

        conda_activate(prefix=self.prefix, working_dir=self.project.directory, env=env)


Environment.update_forward_refs()


class BaseEnvironments(BaseModel):
    def __getitem__(self, key: str) -> Environment:
        return getattr(self, key)

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    class Config:
        allow_mutation = False


class Command(BaseModel):
    name: str
    cmd: str
    environment: Environment
    command_variables: Optional[Dict[str, Optional[str]]] = None
    project: CondaProject

    def run(self, environment=None, extra_args=None, verbose=False) -> NoReturn:
        if environment is None:
            environment = self.environment
        else:
            if isinstance(environment, str):
                environment = self.project.environments[environment]

        if not environment.is_consistent:
            environment.install(verbose=verbose)

        env = prepare_variables(
            self.project.directory,
            self.project._project_file.variables,
            self.command_variables,
        )

        conda_run(
            cmd=self.cmd,
            prefix=environment.prefix,
            working_dir=self.project.directory,
            env=env,
            extra_args=extra_args,
        )

    class Config:
        arbitrary_types_allowed = True


Command.update_forward_refs()


class BaseCommands(BaseModel):
    def __getitem__(self, key: str) -> Command:
        try:
            return getattr(self, key)
        except AttributeError:
            raise CommandNotFoundError(f"The command {key} is not defined.")

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    class Config:
        allow_mutation = False
