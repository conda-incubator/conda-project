# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest


@pytest.fixture(params=[".yml", ".yaml"])
def project_directory_factory(tmp_path, request):
    """A fixture returning a factory function used to create a temporary project directory."""

    def create_project_directory(
        env_yaml: Optional[str] = None,
        project_yaml: Optional[str] = None,
        files: dict[str, str] | None = None,
    ) -> Path:
        """Create a temporary project directory, optionally containing some files.

        Args:
            env_yaml: The contents of the environment file to be included in the project directory. Optional
            project_yaml: The contents of the conda-project file to be included in the project directory. Optional
            files: Additional files to be included in the project directory. The key is the filename,
                and the value is a string of contents to write to the file.

        Returns:
            A path to the temporary project directory.

        """
        suffix = request.param
        if env_yaml is not None:
            env_file = (tmp_path / "environment").with_suffix(suffix)
            with env_file.open("w") as f:
                f.write(env_yaml)

        if project_yaml is not None:
            project_file = (tmp_path / "conda-project").with_suffix(suffix)
            with project_file.open("w") as f:
                f.write(project_yaml)

        files = files or {}
        for fn, contents in files.items():
            path = tmp_path / fn
            with path.open("wt") as f:
                f.write(contents)

        return tmp_path

    create_project_directory._suffix = request.param

    return create_project_directory
