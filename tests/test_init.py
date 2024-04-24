# Copyright (C) 2022-2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import logging
import os
from textwrap import dedent

import pytest
from ruamel.yaml import YAML

from conda_project.conda import call_conda
from conda_project.exceptions import CondaProjectError
from conda_project.project import DEFAULT_PLATFORMS, CondaProject
from conda_project.utils import is_windows


def test_project_init_expanduser(mocker):
    from pathlib import Path

    expanduser = mocker.spy(Path, "expanduser")

    project_directory = "~__a-conda-project-user__/project"

    if is_windows():
        _ = CondaProject(project_directory)
    else:
        with pytest.raises(RuntimeError):
            _ = CondaProject(project_directory)

    assert expanduser.call_count == 1


def test_project_init_new_directory(tmp_path, capsys):
    project_directory = tmp_path / "new-project"
    assert not os.path.exists(project_directory)

    p = CondaProject.init(project_directory, lock_dependencies=False, verbose=True)

    assert os.path.exists(project_directory)
    assert p.project_yaml_path.exists()
    assert p.default_environment.sources[0].exists()
    assert not p.default_environment.is_locked

    assert p.condarc.exists()
    with p.condarc.open() as f:
        condarc = YAML().load(f)
    assert condarc == {}

    out, _ = capsys.readouterr()
    assert f"Project created at {project_directory}\n" == out


def test_project_init_twice(tmp_path, capsys):
    _ = CondaProject.init(tmp_path, lock_dependencies=False)
    p = CondaProject.init(tmp_path, lock_dependencies=False, verbose=True)

    out, _ = capsys.readouterr()
    assert f"Existing project file found at {p.project_yaml_path}.\n" == out


def test_project_init_default_platforms(tmp_path):
    p = CondaProject.init(tmp_path, lock_dependencies=False)

    with p.default_environment.sources[0].open() as f:
        env = YAML().load(f)

    assert env["platforms"] == list(DEFAULT_PLATFORMS)


def test_project_init_specific_platforms(tmp_path):
    p = CondaProject.init(tmp_path, platforms=["linux-64"], lock_dependencies=False)

    with p.default_environment.sources[0].open() as f:
        env = YAML().load(f)

    assert env["platforms"] == ["linux-64"]


def test_project_init_conda_pkgs(tmp_path):
    p = CondaProject.init(
        tmp_path, dependencies=["python=3.10", "numpy"], lock_dependencies=False
    )

    with p.default_environment.sources[0].open() as f:
        env = YAML().load(f)

    assert env["dependencies"] == ["python=3.10", "numpy"]


def test_project_init_pip_pkgs(tmp_path):
    p = CondaProject.init(
        tmp_path,
        dependencies=["python=3.10", "pip", "@pip::numpy"],
        lock_dependencies=False,
    )

    with p.default_environment.sources[0].open() as f:
        env = YAML().load(f)

    assert env["dependencies"] == ["python=3.10", "pip", {"pip": ["numpy"]}]


def test_project_init_pip_pkgs_no_pip(tmp_path, capsys):
    p = CondaProject.init(
        tmp_path, dependencies=["python=3.10", "@pip::numpy"], lock_dependencies=False
    )

    with p.default_environment.sources[0].open() as f:
        env = YAML().load(f)

    assert env["dependencies"] == ["python=3.10", "pip", {"pip": ["numpy"]}]
    assert "do not list pip itself" in capsys.readouterr().out


def test_project_init_specific_channels(tmp_path):
    p = CondaProject.init(
        tmp_path,
        dependencies=["python=3.8", "numpy"],
        channels=["conda-forge", "defaults"],
        lock_dependencies=False,
    )

    with p.default_environment.sources[0].open() as f:
        env = YAML().load(f)

    assert env["dependencies"] == ["python=3.8", "numpy"]
    assert env["channels"] == ["conda-forge", "defaults"]


def test_project_init_default_channel(tmp_path):
    p = CondaProject.init(
        tmp_path, dependencies=["python=3.8", "numpy"], lock_dependencies=False
    )

    with p.default_environment.sources[0].open() as f:
        env = YAML().load(f)

    assert env["dependencies"] == ["python=3.8", "numpy"]
    assert env["channels"] == ["defaults"]


def test_project_init_conda_configs(tmp_path):
    p = CondaProject.init(
        tmp_path,
        dependencies=["python=3.8", "numpy"],
        conda_configs=["experimental_solver=libmamba"],
        lock_dependencies=False,
    )

    with p.condarc.open() as f:
        condarc = YAML().load(f)

    assert condarc["experimental_solver"] == "libmamba"


@pytest.mark.slow
def test_project_init_and_lock(tmp_path):
    p = CondaProject.init(tmp_path, dependencies=["python=3.8"], lock_dependencies=True)
    assert p.default_environment.lockfile.exists()
    assert p.default_environment.lockfile == tmp_path / "conda-lock.default.yml"


def test_project_directory_expanduser(mocker):
    from pathlib import Path

    expanduser = mocker.spy(Path, "expanduser")

    directory = "~__a-conda-project-user__/project"
    if is_windows():
        _ = CondaProject(directory)
    else:
        with pytest.raises(RuntimeError):
            _ = CondaProject(directory)

    assert expanduser.call_count == 1


def test_conda_project_init_empty_dir(tmp_path, caplog):
    caplog.set_level(logging.INFO)

    with pytest.raises(CondaProjectError) as excinfo:
        CondaProject(tmp_path)
    assert "No conda environment.yml or environment.yaml file was found" in str(
        excinfo.value
    )

    assert "No conda-project.yml or conda-project.yaml file was found" in caplog.text


def test_conda_project_init_with_env_yaml(project_directory_factory):
    env_yaml = dedent(
        """\
        name: test
        dependencies: []
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    assert project.default_environment == project.environments["default"]

    assert (
        project.default_environment.lockfile
        == project.directory / "conda-lock.default.yml"
    )
    assert project.default_environment.sources == (
        (project.directory / "environment").with_suffix(
            project_directory_factory._suffix
        ),
    )
    assert project.default_environment.prefix == project.directory / "envs" / "default"


def test_project_init_resolves_cwd(monkeypatch, project_directory_factory):
    project_path = project_directory_factory(env_yaml="")
    monkeypatch.chdir(project_path)

    project = CondaProject()
    assert project.directory.samefile(project_path)


def test_project_init_path(project_directory_factory):
    project_path = project_directory_factory(env_yaml="")

    project = CondaProject(project_path)
    assert project.directory.samefile(project_path)


@pytest.mark.slow
def test_project_init_from_named_env(tmp_path, capsys, empty_conda_environment):
    _ = call_conda(
        ["install", "ca-certificates", "-y", "-p", str(empty_conda_environment)]
    )

    project = CondaProject.init(
        tmp_path, from_environment=empty_conda_environment, verbose=True
    )

    stdout = capsys.readouterr().out
    assert "Reading environment" in stdout
    assert "Constructing lockfile" in stdout
    assert project.default_environment.lockfile.exists()
    assert project.default_environment.sources[0].exists()


@pytest.mark.slow
def test_project_init_from_env_failed(tmp_path, tmp_dir):
    with pytest.raises(ValueError):
        _ = CondaProject.init(tmp_path, from_environment=tmp_dir)
