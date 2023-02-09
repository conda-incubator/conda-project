# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from conda_project.conda import call_conda


@pytest.fixture()
def project_directory_factory(tmp_path, request):
    """A fixture returning a factory function used to create a temporary project directory.

    By default, it will create YAML files with the `.yml` extension. If another test needs
    additional extensions, add a parameterization decorator like:

        @pytest.mark.parametrize('project_directory_factory', ['.yml', '.yaml'], indirect=True)
        def test_something(project_directory_factory):
            ...

    """

    suffix = getattr(request, "param", ".yml")

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
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wt") as f:
                f.write(contents)

        return tmp_path

    create_project_directory._suffix = suffix

    return create_project_directory


@pytest.fixture
def empty_conda_environment(tmp_path):
    args = ["create", "-p", str(tmp_path), "--yes"]
    call_conda(args)
    yield tmp_path


@pytest.fixture
def mocked_execvped(mocker):
    return mocker.patch("conda_project.conda.execvped")
