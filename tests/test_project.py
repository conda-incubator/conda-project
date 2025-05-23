# -*- coding: utf-8 -*-
# Copyright (C) 2022-2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
import os
import platform
from pathlib import Path
from subprocess import CalledProcessError
from textwrap import dedent

import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture
from ruamel.yaml import YAML

from conda_project.conda import call_conda
from conda_project.exceptions import CondaProjectError, CondaProjectLockFailed
from conda_project.project import DEFAULT_PLATFORMS, CondaProject, current_platform


def is_libmamba_installed():
    proc = call_conda(["list", "-n", "base", "conda-libmamba-solver", "--json"])
    result = json.loads(proc.stdout)
    if result:
        return result[0]["name"] == "conda-libmamba-solver"
    else:
        return False


@pytest.mark.slow
def test_install_and_clean(project_directory_factory):
    env_yaml = dedent(
        f"""\
        name: test
        dependencies:
          - python=3.8
        platforms: [{current_platform()}]
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.clean()

    env_dir = project.default_environment.install()
    assert env_dir.samefile(project_path / "envs" / "default")

    conda_history = env_dir / "conda-meta" / "history"
    assert conda_history.exists()

    with conda_history.open() as f:
        assert "create -y --file" in f.read()
    conda_history_mtime = os.path.getmtime(conda_history)

    project.default_environment.install()
    assert conda_history_mtime == os.path.getmtime(conda_history)

    project.default_environment.install(force=True)
    assert conda_history_mtime < os.path.getmtime(conda_history)

    project.default_environment.clean()
    assert not conda_history.exists()
    assert not project.default_environment.is_consistent


@pytest.mark.slow
def test_lock(project_directory_factory):
    env_yaml = dedent(
        f"""\
        name: test
        dependencies:
          - python=3.8
        platforms: [{current_platform()}]
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock()

    lockfile = project_path / "conda-lock.default.yml"
    assert lockfile == project.default_environment.lockfile
    assert lockfile.exists()
    assert project.default_environment.is_locked


@pytest.mark.slow
def test_lock_message_supplied_platforms(
    project_directory_factory, mocker: MockerFixture
):
    import conda_project.project

    spinner = mocker.spy(conda_project.project, "Spinner")

    env_yaml = dedent(
        """\
        name: test
        dependencies:
          - python=3.8
        platforms: [osx-arm64, linux-64]
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock(verbose=True)

    assert (
        spinner.call_args.kwargs["prefix"]
        == "Locking dependencies for environment default on platforms linux-64, osx-arm64"
    )


@pytest.mark.slow
def test_lock_message_default_platforms(
    project_directory_factory, mocker: MockerFixture
):
    import conda_project.project

    spinner = mocker.spy(conda_project.project, "Spinner")

    env_yaml = dedent(
        """\
        name: test
        dependencies:
          - python=3.8
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock(verbose=True)

    platforms = ", ".join(sorted(DEFAULT_PLATFORMS))
    assert (
        spinner.call_args.kwargs["prefix"]
        == f"Locking dependencies for environment default on platforms {platforms}"
    )


def test_lock_failed_from_conda(project_directory_factory):
    env_yaml = dedent(
        """\
        name: test
        dependencies: []
        """
    )
    condarc = "channels: {___}"
    project_path = project_directory_factory(
        env_yaml=env_yaml, files={".condarc": condarc}
    )

    project = CondaProject(project_path)
    with pytest.raises(CondaProjectLockFailed):
        project.default_environment.lock()


def test_lock_conda_serialization_error(
    mocker: MockerFixture, project_directory_factory
):
    env_yaml = dedent(
        """\
        name: test
        dependencies: []
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    mocker.patch(
        "conda_project.project.make_lock_files",
        autospec=True,
        side_effect=CalledProcessError(
            returncode=1,
            cmd="conda",
            output='{"serializable": True}',
            stderr="output is not json formatted",
        ),
    )

    project = CondaProject(project_path)
    with pytest.raises(CondaProjectLockFailed) as excinfo:
        project.default_environment.lock()
        assert "output is not json formatted" == str(excinfo.value)


def test_lock_no_channels(project_directory_factory):
    env_yaml = dedent(
        f"""\
        name: test
        dependencies: []
        platforms: [{current_platform()}]
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)

    with pytest.warns(UserWarning, match=r"there are no 'channels:' key.*"):
        project.default_environment.lock(verbose=True)

    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)

    assert [c["url"] for c in lock["metadata"]["channels"]] == ["defaults"]


def test_lock_with_channels(project_directory_factory):
    env_yaml = dedent(
        f"""\
        name: test
        channels: [defusco, conda-forge, defaults]
        dependencies: []
        platforms: [{current_platform()}]
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock()

    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)

    assert [c["url"] for c in lock["metadata"]["channels"]] == [
        "defusco",
        "conda-forge",
        "defaults",
    ]


def test_lock_no_platforms(project_directory_factory):
    env_yaml = dedent(
        """\
        name: test
        dependencies: []
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock()

    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)

    assert lock["metadata"]["platforms"] == list(DEFAULT_PLATFORMS)


def test_lock_with_platforms(project_directory_factory):
    env_yaml = dedent(
        """\
        name: test
        dependencies: []
        platforms: [linux-64, osx-64]
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock(verbose=True)

    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)

    assert lock["metadata"]["platforms"] == ["linux-64", "osx-64"]


def test_force_relock(project_directory_factory, capsys):
    env_yaml = dedent(
        f"""\
        name: test
        dependencies: []
        platforms: [{current_platform()}]
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock(verbose=True)
    stdout = capsys.readouterr().out
    assert project.default_environment.is_locked

    lockfile_mtime = os.path.getmtime(project.default_environment.lockfile)
    project.default_environment.lock(verbose=True)
    stdout = capsys.readouterr().out
    assert (
        "The lockfile conda-lock.default.yml already exists and is up-to-date."
        in stdout
    )
    assert lockfile_mtime == os.path.getmtime(project.default_environment.lockfile)

    project.default_environment.lock(force=True)
    assert lockfile_mtime < os.path.getmtime(project.default_environment.lockfile)


def test_lock_outdated(project_directory_factory):
    env_yaml = dedent(
        f"""\
        name: test
        dependencies: []
        platforms: [{current_platform()}]
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock(verbose=True)
    assert project.default_environment.is_locked

    updated_env_yaml = dedent(
        f"""\
        name: test
        dependencies:
          - python=3.8
        platforms: [{current_platform()}]
        """
    )
    with (project.default_environment.sources[0]).open("wt") as f:
        f.write(updated_env_yaml)

    assert not project.default_environment.is_locked


@pytest.mark.slow
def test_relock_add_packages(project_directory_factory):
    env_yaml = dedent(
        f"""\
        name: test
        dependencies:
          - python=3.8
        platforms: [{current_platform()}]
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock()

    assert project.default_environment.lockfile.exists()
    lockfile_mtime = os.path.getmtime(project.default_environment.lockfile)
    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)
    assert "python" in [p["name"] for p in lock["package"]]
    assert "requests" not in [p["name"] for p in lock["package"]]

    env_yaml = dedent(
        f"""\
        name: test
        dependencies:
          - python=3.8
          - requests
        platforms: [{current_platform()}]
        """
    )
    with project.default_environment.sources[0].open("w") as f:
        f.write(env_yaml)

    assert not project.default_environment.is_locked

    project.default_environment.lock()
    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)
    assert "python" in [p["name"] for p in lock["package"]]
    assert "requests" in [p["name"] for p in lock["package"]]

    assert lockfile_mtime < os.path.getmtime(project.default_environment.lockfile)


@pytest.mark.slow
def test_relock_remove_packages(project_directory_factory):
    env_yaml = dedent(
        f"""\
        name: test
        dependencies:
          - python=3.8
          - requests
        platforms: [{current_platform()}]
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock()

    assert project.default_environment.lockfile.exists()
    lockfile_mtime = os.path.getmtime(project.default_environment.lockfile)
    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)
    assert "python" in [p["name"] for p in lock["package"]]
    assert "requests" in [p["name"] for p in lock["package"]]

    env_yaml = dedent(
        f"""\
        name: test
        dependencies:
          - python=3.8
        platforms: [{current_platform()}]
        """
    )
    with project.default_environment.sources[0].open("w") as f:
        f.write(env_yaml)

    project.default_environment.lock()
    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)
    assert "python" in [p["name"] for p in lock["package"]]
    assert "requests" not in [p["name"] for p in lock["package"]]

    assert lockfile_mtime < os.path.getmtime(project.default_environment.lockfile)


@pytest.mark.slow
def test_relock_failed(project_directory_factory):
    env_yaml = dedent(
        f"""\
        name: test
        dependencies:
          - python=3.8
          - requests
        platforms: [{current_platform()}]
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock()

    assert project.default_environment.lockfile.exists()
    lockfile_mtime = os.path.getmtime(project.default_environment.lockfile)
    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)
    assert "python" in [p["name"] for p in lock["package"]]
    assert "requests" in [p["name"] for p in lock["package"]]

    env_yaml = dedent(
        f"""\
        name: test
        dependencies:
          - python=3.8
          - _bad-package-8933
        platforms: [{current_platform()}]
        """
    )
    with project.default_environment.sources[0].open("w") as f:
        f.write(env_yaml)

    with pytest.raises(CondaProjectError):
        project.default_environment.lock()

    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)
    assert "python" in [p["name"] for p in lock["package"]]
    assert "requests" in [p["name"] for p in lock["package"]]
    assert "_bad-package-8933" not in [p["name"] for p in lock["package"]]

    assert lockfile_mtime == os.path.getmtime(project.default_environment.lockfile)


def test_project_named_environment(project_directory_factory):
    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"

    project_yaml = dedent(
        f"""\
        name: test
        environments:
          standard: [environment{project_directory_factory._suffix}]
        """
    )

    project_path = project_directory_factory(
        env_yaml=env_yaml, project_yaml=project_yaml
    )
    project = CondaProject(project_path)

    assert project.environments.keys() == {"standard"}
    assert (
        project.environments["standard"]
        .sources[0]
        .samefile(
            (project_path / "environment").with_suffix(
                project_directory_factory._suffix
            )
        )
    )
    assert project.default_environment == project.environments["standard"]
    assert (
        project.environments["standard"].prefix
        == project.directory / "envs" / "standard"
    )


def test_project_hyphen_named_environment(project_directory_factory):
    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"

    project_yaml = dedent(
        f"""\
        name: test
        environments:
          my-env: [environment{project_directory_factory._suffix}]
        """
    )

    project_path = project_directory_factory(
        env_yaml=env_yaml, project_yaml=project_yaml
    )
    project = CondaProject(project_path)

    assert project.environments.keys() == {"my-env"}
    assert (
        project.environments["my-env"]
        .sources[0]
        .samefile(
            (project_path / "environment").with_suffix(
                project_directory_factory._suffix
            )
        )
    )
    assert project.default_environment == project.environments["my-env"]
    assert (
        project.environments["my-env"].prefix == project.directory / "envs" / "my-env"
    )


def test_project_environment_envs_path_specified(
    tmp_dir: Path, project_directory_factory, monkeypatch: MonkeyPatch
):
    test_envs_path = tmp_dir / "apples"
    monkeypatch.setenv("CONDA_PROJECT_ENVS_PATH", str(test_envs_path))
    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)
    assert project.default_environment.prefix == test_envs_path / "default"


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Windows has a hard time with read-only directories",
)
def test_project_environment_envs_path_uses_first_writable(
    project_directory_factory, monkeypatch
):
    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"
    project_path = project_directory_factory(env_yaml=env_yaml)

    test_envs_path1 = project_path / "apples"
    test_envs_path1.mkdir(mode=0o555)
    test_envs_path2 = project_path / "bananas"
    test_envs_path2.mkdir(mode=0o777)

    monkeypatch.setenv(
        "CONDA_PROJECT_ENVS_PATH",
        f"{str(test_envs_path1)}{os.pathsep}{str(test_envs_path2)}",
    )

    project = CondaProject(project_path)

    # Since the first path was not writable, should use the second path
    assert (
        project.default_environment.prefix == project.directory / "bananas" / "default"
    )


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Windows has a hard time with read-only directories",
)
def test_project_environment_envs_path_none_writable_uses_default(
    project_directory_factory, monkeypatch
):
    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"
    project_path = project_directory_factory(env_yaml=env_yaml)

    test_envs_path1 = project_path / "apples"
    test_envs_path1.mkdir(mode=0o555)

    monkeypatch.setenv(
        "CONDA_PROJECT_ENVS_PATH",
        str(test_envs_path1),
    )
    project = CondaProject(project_path)

    # Since the specified path was not writable, should fall back to default
    assert project.default_environment.prefix == project.directory / "envs" / "default"


def test_project_environment_envs_path_creates_directory(
    tmp_dir, project_directory_factory, monkeypatch
):
    test_envs_path = tmp_dir / "apples"
    monkeypatch.setenv(
        "CONDA_PROJECT_ENVS_PATH",
        str(test_envs_path),
    )
    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)
    assert project.default_environment.prefix == test_envs_path / "default"

    assert not test_envs_path.exists()

    project.default_environment.install()

    assert test_envs_path.exists()
    assert (test_envs_path / "default").exists()


@pytest.mark.parametrize("envs_path", ["apples", "./apples"])
def test_project_environment_envs_path_relative_path(
    project_directory_factory, monkeypatch, envs_path
):
    monkeypatch.setenv(
        "CONDA_PROJECT_ENVS_PATH",
        envs_path,
    )
    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)
    assert (
        project.default_environment.prefix == project.directory / "apples" / "default"
    )


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Windows has a hard time with read-only directories",
)
def test_project_environment_envs_path_creates_first_possible_dir(
    tmp_dir, project_directory_factory, monkeypatch
):

    test_envs_path1 = tmp_dir / "apples"
    test_envs_path1.mkdir(mode=0o555)
    test_envs_path2 = tmp_dir / "bananas"
    test_envs_path2.mkdir(mode=0o777)

    # apples/worm:bananas/tree
    envs_path = f"{test_envs_path1 / 'worm'}{os.pathsep}{test_envs_path2 / 'tree'}"
    monkeypatch.setenv(
        "CONDA_PROJECT_ENVS_PATH",
        envs_path,
    )
    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)
    assert (
        project.default_environment.prefix == tmp_dir / "bananas" / "tree" / "default"
    )


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Windows has a hard time with read-only directories",
)
def test_project_environment_envs_path_project_dir_not_writable(
    tmp_dir, project_directory_factory, monkeypatch
):
    writable_envs_path = tmp_dir / "bananas"
    envs_path = f"./apples{os.pathsep}{writable_envs_path}"
    monkeypatch.setenv(
        "CONDA_PROJECT_ENVS_PATH",
        f"envs{os.pathsep}{envs_path}",
    )
    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)
    project.default_environment.lock()

    project_path.chmod(mode=0o555)
    assert project.default_environment.prefix == writable_envs_path / "default"

    assert not project.default_environment.prefix.exists()
    project.default_environment.install()

    assert (project.default_environment.prefix / "conda-meta" / "history").exists()


def test_project_environments_immutable(project_directory_factory):
    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"

    project_yaml = dedent(
        f"""\
        name: test
        environments:
          default: [env{project_directory_factory._suffix}]
        """
    )

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={f"env{project_directory_factory._suffix}": env_yaml},
    )
    project = CondaProject(project_path)

    with pytest.raises(TypeError):
        project.default_environment.sources[0] = ("empty",)

    with pytest.raises(TypeError):
        project.environments["new"] = project.default_environment

    with pytest.raises(TypeError):
        project.environments["default"] = project.default_environment

    with pytest.raises(TypeError):
        project.environments.default = project.default_environment


def test_project_multiple_envs(project_directory_factory):
    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"

    project_yaml = dedent(
        f"""\
        name: test
        environments:
          bbb: [env1{project_directory_factory._suffix}]
          default: [env2{project_directory_factory._suffix}]
        """
    )

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"env1{project_directory_factory._suffix}": env_yaml,
            f"env2{project_directory_factory._suffix}": env_yaml,
        },
    )
    project = CondaProject(project_path)

    assert project.environments.keys() == {"bbb", "default"}
    assert project.default_environment.name == "bbb"


def test_lock_install_clean_default_with_multiple_envs(project_directory_factory):
    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"

    project_yaml = dedent(
        f"""\
        name: test
        environments:
          bbb: [env1{project_directory_factory._suffix}]
          default: [env2{project_directory_factory._suffix}]
        """
    )

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"env1{project_directory_factory._suffix}": env_yaml,
            f"env2{project_directory_factory._suffix}": env_yaml,
        },
    )
    project = CondaProject(project_path)
    project.default_environment.lock()
    project.default_environment.install()

    assert project.default_environment.lockfile.samefile(
        project_path / "conda-lock.bbb.yml"
    )
    assert project.default_environment.lockfile.exists()

    assert project.default_environment.prefix.samefile(project_path / "envs" / "bbb")
    assert (project.default_environment.prefix / "conda-meta" / "history").exists()

    project.default_environment.clean()
    assert not project.default_environment.prefix.exists()


def test_lock_install_clean_named_with_multiple_envs(project_directory_factory):
    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"

    project_yaml = dedent(
        f"""\
        name: test
        environments:
          bbb: [env1{project_directory_factory._suffix}]
          default: [env2{project_directory_factory._suffix}]
        """
    )

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"env1{project_directory_factory._suffix}": env_yaml,
            f"env2{project_directory_factory._suffix}": env_yaml,
        },
    )
    project = CondaProject(project_path)
    project.environments["default"].lock()
    project.environments["default"].install()

    assert project.environments["default"].lockfile.samefile(
        project_path / "conda-lock.default.yml"
    )
    assert project.environments["default"].lockfile.exists()

    assert project.environments["default"].prefix.samefile(
        project_path / "envs" / "default"
    )
    assert (project.environments["default"].prefix / "conda-meta" / "history").exists()

    project.environments["default"].clean()
    assert not project.environments["default"].prefix.exists()


def test_lock_install_clean_multiple_envs(project_directory_factory):
    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"

    project_yaml = dedent(
        f"""\
        name: test
        environments:
          bbb: [env1{project_directory_factory._suffix}]
          default: [env2{project_directory_factory._suffix}]
        """
    )

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"env1{project_directory_factory._suffix}": env_yaml,
            f"env2{project_directory_factory._suffix}": env_yaml,
        },
    )
    project = CondaProject(project_path)

    project.environments["bbb"].lock()
    project.environments["bbb"].install()

    assert project.environments["bbb"].lockfile.samefile(
        project_path / "conda-lock.bbb.yml"
    )
    assert project.environments["bbb"].lockfile.exists()

    assert project.environments["bbb"].prefix.samefile(project_path / "envs" / "bbb")
    assert (project.environments["bbb"].prefix / "conda-meta" / "history").exists()

    project.environments["default"].lock()
    project.environments["default"].install()

    assert project.environments["default"].lockfile.samefile(
        project_path / "conda-lock.default.yml"
    )
    assert project.environments["default"].lockfile.exists()

    assert project.environments["default"].prefix.samefile(
        project_path / "envs" / "default"
    )
    assert (project.environments["default"].prefix / "conda-meta" / "history").exists()

    project.environments["bbb"].clean()
    assert not project.environments["bbb"].prefix.exists()

    project.environments["default"].clean()
    assert not project.environments["default"].prefix.exists()


@pytest.mark.slow
def test_project_lock_env_multiple_sources(project_directory_factory):
    environment_yml = f"dependencies: [python]\nplatforms: [{current_platform()}]"
    extras_yml = f"dependencies: [requests]\nplatforms: [{current_platform()}]"

    project_yaml = dedent(
        f"""\
        name: test
        environments:
          default:
            - environment{project_directory_factory._suffix}
            - extras{project_directory_factory._suffix}
        """
    )

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"environment{project_directory_factory._suffix}": environment_yml,
            f"extras{project_directory_factory._suffix}": extras_yml,
        },
    )
    project = CondaProject(project_path)
    project.default_environment.lock()

    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)

    assert lock["metadata"]["sources"] == [
        f"environment{project_directory_factory._suffix}",
        f"extras{project_directory_factory._suffix}",
    ]

    assert "requests" in [p["name"] for p in lock["package"]]
    assert "python" in [p["name"] for p in lock["package"]]


@pytest.mark.slow
def test_project_lock_env_multiple_sources_different_directories(
    project_directory_factory,
):
    environment_yml = f"dependencies: [python]\nplatforms: [{current_platform()}]"
    extras_yml = f"dependencies: [requests]\nplatforms: [{current_platform()}]"

    project_yaml = dedent(
        f"""\
        name: test
        environments:
          default:
            - ./environment{project_directory_factory._suffix}
            - ../extras{project_directory_factory._suffix}
        """
    )

    project_path = project_directory_factory(
        files={
            f"project/conda-project{project_directory_factory._suffix}": project_yaml,
            f"project/environment{project_directory_factory._suffix}": environment_yml,
            f"extras{project_directory_factory._suffix}": extras_yml,
        },
    )
    project = CondaProject(project_path / "project")

    assert project.default_environment.sources[0].samefile(
        project_path / "project" / f"environment{project_directory_factory._suffix}"
    )
    assert project.default_environment.sources[1].samefile(
        project_path / f"extras{project_directory_factory._suffix}"
    )

    project.default_environment.lock()

    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)

    assert (project.directory / lock["metadata"]["sources"][0]).samefile(
        project_path / "project" / f"environment{project_directory_factory._suffix}"
    )
    assert (project.directory / lock["metadata"]["sources"][1]).samefile(
        project_path / f"extras{project_directory_factory._suffix}"
    )

    assert "requests" in [p["name"] for p in lock["package"]]
    assert "python" in [p["name"] for p in lock["package"]]


@pytest.mark.skipif(
    not is_libmamba_installed(), reason="Libmamba solver not installed."
)
def test_failed_to_solve_libmamba(project_directory_factory):
    env_yaml = dedent(
        f"""\
        name: fail
        channels:
          - conda-forge

        dependencies:
          - ensureconda
          - conda-token
        platforms: [{current_platform()}]
        """
    )

    condarc = "experimental_solver: libmamba"

    project_path = project_directory_factory(
        env_yaml=env_yaml, files={".condarc": condarc}
    )
    project = CondaProject(project_path)

    with pytest.raises(CondaProjectLockFailed):
        project.default_environment.lock()


@pytest.mark.skipif(
    not is_libmamba_installed(), reason="Libmamba solver not installed."
)
def test_failed_to_solve_classic(project_directory_factory):
    env_yaml = dedent(
        f"""\
        name: fail
        channels:
          - conda-forge

        dependencies:
          - ensureconda
          - conda-token
        platforms: [{current_platform()}]
        """
    )
    condarc = "experimental_solver: classic"

    project_path = project_directory_factory(
        env_yaml=env_yaml, files={".condarc": condarc}
    )
    project = CondaProject(project_path)

    with pytest.raises(CondaProjectError) as exinfo:
        project.default_environment.lock()

    assert "The following packages are not available from current channels:" in str(
        exinfo.value
    )


def test_check_multi_env(project_directory_factory, capsys):
    env1 = env2 = f"dependencies: []\nplatforms: [{current_platform()}]"
    project_yaml = dedent(
        f"""\
        name: multi-envs
        environments:
          env1: [env1{project_directory_factory._suffix}]
          env2: [env2{project_directory_factory._suffix}]
        """
    )
    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"env1{project_directory_factory._suffix}": env1,
            f"env2{project_directory_factory._suffix}": env2,
        },
    )

    project = CondaProject(project_path)
    assert not project.check(verbose=True)

    assert "is not locked" in capsys.readouterr().err

    project.environments["env1"].lock()
    assert not project.check()

    project.environments["env2"].lock()
    assert project.check()

    env1 = f"dependencies: [python=3.8]\nplatforms: [{current_platform()}]"
    with (project_path / f"env1{project_directory_factory._suffix}").open("w") as f:
        f.write(env1)

    assert not project.check(verbose=True)

    assert "is out-of-date" in capsys.readouterr().err
