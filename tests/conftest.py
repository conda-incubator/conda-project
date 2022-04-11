# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import pytest
from functools import partial
from pathlib import Path


@pytest.fixture(params=['environment.yml', 'environment.yaml'])
def project_directory(tmpdir, request):
    def __project_directory(env_fn, env_yaml='', files=None):
        env_file = tmpdir.join(env_fn)
        env_file.write(env_yaml)

        if files is not None:
            for fn, contents in files.items():
                path = Path(tmpdir) / fn
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'wt') as f:
                    f.write(contents)

        return tmpdir

    return partial(__project_directory, env_fn=request.param)
