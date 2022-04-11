# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import pytest


@pytest.fixture(params=['environment.yml', 'environment.yaml'])
def project_directory_factory(tmp_path, request):
    """A fixture returning a factory function used to create a temporary project directory."""
    def _create_project_directory(env_yaml: str = '', files=None):
        """Create a temporary project directory, optionally containing some files.

        Args:
            env_yaml: The contents of the environment file to be included in the project directory.
            files: Additional files to be included in the project directory.

        Returns:
            A path to the temporary project directory.

        """
        env_filename = request.param
        env_file = tmp_path / env_filename
        with env_file.open("w") as fp:
            fp.write(env_yaml)

        if files is not None:
            for fn, contents in files.items():
                path = tmp_path / fn
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('wt') as f:
                    f.write(contents)

        return tmp_path

    return _create_project_directory
