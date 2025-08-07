# Copyright (C) 2022-2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from textwrap import dedent

import pytest

from conda_project._conda_lock import is_conda_lock_3
from conda_project.conda import current_platform
from conda_project.exceptions import CondaProjectLockFailed
from conda_project.project import CondaProject

VIRTUAL_PACKAGES = dedent(
    """\
    subdirs:
      linux-64:
        packages:
          __archspec: "1 x86_64_v2"
      osx-64:
        packages:
          __archspec: "1 x86_64_v2"
      osx-arm64:
        packages:
          __archspec: "1 x86_64_v2"
      win-64:
        packages:
          __archspec: "1 x86_64_v2"
"""
)


@pytest.mark.parametrize(
    "virtual_package_fn", ("virtual-packages.yml", "virtual-packages.yaml", None)
)
def test_virtual_package_yaml(
    project_directory_factory, virtual_package_fn, capsys
) -> None:
    env_yaml = dedent(
        f"""\
        name: virtual-packages
        channels: [defaults]
        dependencies: [_x86_64-microarch-level=2]
        platforms: [{current_platform()}]
    """
    )

    if virtual_package_fn is None:
        project_path = project_directory_factory(env_yaml=env_yaml)
        project = CondaProject(project_path)
        assert project.get_virtual_package_spec() is None

        with pytest.raises(CondaProjectLockFailed):
            project.default_environment.lock()

    else:
        project_path = project_directory_factory(
            env_yaml=env_yaml, files={virtual_package_fn: VIRTUAL_PACKAGES}
        )
        project = CondaProject(project_path)
        spec = project.get_virtual_package_spec()
        assert spec
        assert spec.name == virtual_package_fn

        if is_conda_lock_3():
            project.default_environment.lock(verbose=True)
            out, _ = capsys.readouterr()
            assert "Using virtual packages" in out
        else:
            with pytest.raises(CondaProjectLockFailed):
                project.default_environment.lock(verbose=True)
            out, _ = capsys.readouterr()
            assert "Consider upgrading to version 3" in out
