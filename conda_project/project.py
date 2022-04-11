# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from pathlib import Path

from .conda import call_conda
from .exceptions import CondaProjectError

ENVIRONMENT_YAML_FILENAMES = ("environment.yml", "environment.yaml")


class CondaProject:
    """A project managed by `conda-project`.

    Attributes:
        directory: The project base directory. Defaults to the current working directory.
        condarc: A path to the local `.condarc` file. Defaults to `<directory>/.condarc`.
        environment_file: A path to the environment file.

    Args:
        directory: The project base directory.

    Raises:
        CondaProjectError: If no suitable environment file is found.

    """

    def __init__(self, directory: Path | str = "."):
        self.directory = Path(directory).resolve()
        self.condarc = self.directory / ".condarc"
        self.environment_file = self._find_environment_file()

    def _find_environment_file(self) -> Path:
        """Find an environment file in the project directory.

        Raises:
            CondaProjectError: If no suitable environment file can be found.

        """
        for filename in ENVIRONMENT_YAML_FILENAMES:
            path = self.directory / filename
            if path.exists():
                return path
        raise CondaProjectError(
            f"No Conda environment.yml or environment.yaml file was found in {self.directory}."
        )

    @property
    def default_env(self) -> Path:
        """A path to the default conda environment."""
        return self.directory / "envs" / "default"

    def prepare(self, force: bool = False, verbose: bool = False) -> Path:
        """Prepare the default conda environment.

        Creates a new conda environment and installs the packages from the environment.yaml file.

        Args:
            force: If True, will force creation of a new conda environment.
            verbose: A verbose flag passed into the `conda create` command.

        Returns:
            A path to the created environment.

        """
        default_env = self.default_env
        conda_meta = os.path.join(default_env, "conda-meta", "history")
        if os.path.exists(conda_meta) and not force:
            return default_env
        else:
            args = [
                "env",
                "create",
                "-f",
                str(self.environment_file),
                "-p",
                str(default_env),
            ]
            if force:
                args.append("--force")

            _ = call_conda(
                args,
                condarc_path=self.condarc,
                verbose=verbose,
            )
            return default_env

    def clean(self, verbose: bool = False) -> None:
        """Remove the default conda environment."""
        _ = call_conda(
            ["env", "remove", "-p", str(self.default_env)],
            condarc_path=self.condarc,
            verbose=verbose,
        )
