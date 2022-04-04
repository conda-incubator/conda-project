# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import pytest
from pathlib import Path


@pytest.fixture(params=['environment.yml', 'environment.yaml'])
def project_directory(tmpdir, request):
    """A fixture returning a function used to create a temporary project directory."""
    def __project_directory(env_yaml='', files=None):
        """Create a temporary project directory, optionally containing some files.

        Args:
            env_yaml: The environment file to be included in the project directory.
            files: Additional files to be included in the project directory.

        Returns:
            A path to the temporary project directory.

        """
        env_fn = request.param
        env_file = tmpdir.join(env_fn)
        env_file.write(env_yaml)

        if files is not None:
            for fn, contents in files.items():
                path = Path(tmpdir) / fn
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('wt') as f:
                    f.write(contents)

        return tmpdir

    return __project_directory
