# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os

import pytest
from pathlib import Path
from ruamel.yaml import YAML

from conda_project.exceptions import CondaProjectError
from conda_project.project import DEFAULT_PLATFORMS, CondaProject


def test_project_create_new_directory(tmpdir, capsys):
    project_directory = os.path.join(tmpdir, "new-project")
    assert not os.path.exists(project_directory)

    p = CondaProject.create(project_directory, lock_dependencies=False, verbose=True)

    assert os.path.exists(project_directory)
    assert p.project_yaml_path.exists()
    assert p.default_environment.sources[0].exists()

    out, _ = capsys.readouterr()
    assert f"Project created at {project_directory}\n" == out


def test_project_create_default_platforms(tmpdir):
    p = CondaProject.create(tmpdir, lock_dependencies=False)

    with p.default_environment.sources[0].open() as f:
        env = YAML().load(f)

    assert env["platforms"] == list(DEFAULT_PLATFORMS)


def test_project_create_specific_platforms(tmpdir):
    p = CondaProject.create(tmpdir, platforms=["linux-64"], lock_dependencies=False)

    with p.default_environment.sources[0].open() as f:
        env = YAML().load(f)

    assert env["platforms"] == ["linux-64"]


def test_project_create_specific_channels(tmpdir):
    p = CondaProject.create(
        tmpdir,
        dependencies=["python=3.8", "numpy"],
        channels=["conda-forge", "defaults"],
        lock_dependencies=False,
    )

    with p.default_environment.sources[0].open() as f:
        env = YAML().load(f)

    assert env["dependencies"] == ["python=3.8", "numpy"]
    assert env["channels"] == ["conda-forge", "defaults"]


def test_project_create_default_channel(tmpdir):
    p = CondaProject.create(
        tmpdir, dependencies=["python=3.8", "numpy"], lock_dependencies=False
    )

    with p.default_environment.sources[0].open() as f:
        env = YAML().load(f)

    assert env["dependencies"] == ["python=3.8", "numpy"]
    assert env["channels"] == ["defaults"]


def test_project_create_conda_configs(tmpdir):
    p = CondaProject.create(
        tmpdir,
        dependencies=["python=3.8", "numpy"],
        conda_configs=["experimental_solver=libmamba"],
        lock_dependencies=False,
    )

    with open(p.condarc) as f:
        condarc = YAML().load(f)

    assert condarc["experimental_solver"] == "libmamba"


@pytest.mark.slow
def test_project_create_and_lock(tmpdir):
    p = CondaProject.create(tmpdir, dependencies=["python=3.8"], lock_dependencies=True)
    assert p.default_environment.lockfile.exists()
    assert p.default_environment.lockfile == Path(tmpdir) / "default.conda-lock.yml"


def test_conda_project_init_empty_dir(tmpdir, capsys, monkeypatch):
    monkeypatch.setenv("CONDA_PROJECT_LOGLEVEL", "INFO")

    with pytest.raises(CondaProjectError) as excinfo:
        CondaProject(tmpdir)
    assert "No Conda environment.yml or environment.yaml file was found" in str(
        excinfo.value
    )

    logs = capsys.readouterr()
    assert "No conda-project.yml or conda-project.yaml file was found" in logs.err


def test_conda_project_init_with_env_yaml(project_directory_factory):
    env_yaml = """name: test
dependencies: []
"""
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    assert project.default_environment == project.environments["default"]

    assert (
        project.default_environment.lockfile
        == project.directory / "default.conda-lock.yml"
    )
    assert project.default_environment.sources == [
        (project.directory / "environment").with_suffix(
            project_directory_factory._suffix
        )
    ]
    assert project.default_environment.prefix == project.directory / "envs" / "default"


def test_project_init_expands_cwd(monkeypatch, project_directory_factory):
    project_path = project_directory_factory(env_yaml="")
    monkeypatch.chdir(project_path)

    project = CondaProject()
    assert project.directory.samefile(project_path)


def test_project_init_path(project_directory_factory):
    project_path = project_directory_factory(env_yaml="")

    project = CondaProject(project_path)
    assert project.directory.samefile(project_path)


def test_prepare_no_dependencies(project_directory_factory):
    env_yaml = """name: test
dependencies: []
"""
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    env_dir = project.prepare()
    assert env_dir.samefile(project_path / "envs" / "default")

    conda_history = env_dir / "conda-meta" / "history"
    assert conda_history.exists()


def test_prepare_env_exists(project_directory_factory, capsys):
    env_yaml = """name: test
dependencies: []
"""
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    env_dir = project.prepare(verbose=True)

    out, _ = capsys.readouterr()
    assert f"environment created at {env_dir}" == out.splitlines()[-1]

    _ = project.prepare(verbose=True)

    out, _ = capsys.readouterr()
    assert "The environment already exists" in out.splitlines()[-1]


@pytest.mark.slow
def test_prepare_and_clean(project_directory_factory):
    env_yaml = """name: test
dependencies:
  - python=3.8
"""
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    env_dir = project.prepare()
    assert env_dir.samefile(project_path / "envs" / "default")

    conda_history = env_dir / "conda-meta" / "history"
    assert conda_history.exists()

    with conda_history.open() as f:
        assert "create -y --file" in f.read()
    conda_history_mtime = os.path.getmtime(conda_history)

    project.prepare()
    assert conda_history_mtime == os.path.getmtime(conda_history)

    project.prepare(force=True)
    assert conda_history_mtime < os.path.getmtime(conda_history)

    project.clean()
    assert not conda_history.exists()


@pytest.mark.slow
def test_lock(project_directory_factory):
    env_yaml = """name: test
dependencies:
  - python=3.8
"""
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.lock()

    lockfile = project_path / "default.conda-lock.yml"
    assert lockfile == project.default_environment.lockfile
    assert lockfile.exists()


def test_lock_no_channels(project_directory_factory):
    env_yaml = """name: test
dependencies: []
"""
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)

    with pytest.warns(UserWarning, match=r"there are no 'channels:' key.*"):
        project.lock(verbose=True)

    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)

    assert [c["url"] for c in lock["metadata"]["channels"]] == ["defaults"]


def test_lock_with_channels(project_directory_factory):
    env_yaml = """name: test
channels: [defusco, conda-forge, defaults]
dependencies: []
"""
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.lock()

    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)

    assert [c["url"] for c in lock["metadata"]["channels"]] == [
        "defusco",
        "conda-forge",
        "defaults",
    ]


def test_lock_no_platforms(project_directory_factory):
    env_yaml = """name: test
dependencies: []
"""
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.lock()

    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)

    assert lock["metadata"]["platforms"] == list(DEFAULT_PLATFORMS)


def test_lock_with_platforms(project_directory_factory):
    env_yaml = """name: test
dependencies: []
platforms: [linux-64, osx-64]
"""
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.lock(verbose=True)

    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)

    assert lock["metadata"]["platforms"] == ["linux-64", "osx-64"]


def test_lock_wrong_platform(project_directory_factory):
    env_yaml = """name: test
dependencies: []
platforms: [dummy-platform]
"""

    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.lock()

    with pytest.raises(CondaProjectError) as e:
        project.prepare()
    assert "not in the supported locked platforms" in str(e.value)


def test_force_relock(project_directory_factory):
    env_yaml = """name: test
dependencies: []
"""
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.lock(verbose=True)

    lockfile_mtime = os.path.getmtime(project.default_environment.lockfile)
    project.lock()
    assert lockfile_mtime == os.path.getmtime(project.default_environment.lockfile)

    project.lock(force=True)
    assert lockfile_mtime < os.path.getmtime(project.default_environment.lockfile)


@pytest.mark.slow
def test_relock_add_packages(project_directory_factory):
    env_yaml = """name: test
dependencies:
  - python=3.8
"""
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.lock()

    assert project.default_environment.lockfile.exists()
    lockfile_mtime = os.path.getmtime(project.default_environment.lockfile)
    with project.default_environment.lockfile.open() as f:
        lock = f.read()
    assert "requests" not in lock

    env_yaml = """name: test
dependencies:
  - python=3.8
  - requests
"""
    with project.default_environment.sources[0].open("w") as f:
        f.write(env_yaml)

    project.lock()
    with project.default_environment.lockfile.open() as f:
        lock = f.read()
    assert "requests" in lock

    assert lockfile_mtime < os.path.getmtime(project.default_environment.lockfile)


def test_project_renamed_environment(project_directory_factory):
    env_yaml = """dependencies: []
"""

    project_yaml = f"""name: test
environments:
  standard: [environment{project_directory_factory._suffix}]
"""

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


def test_prepare_renamed_environment(project_directory_factory):
    env_yaml = """dependencies: []
"""

    project_yaml = f"""name: test
environments:
  standard: [environment{project_directory_factory._suffix}]
"""

    project_path = project_directory_factory(
        env_yaml=env_yaml, project_yaml=project_yaml
    )
    project = CondaProject(project_path)
    project.lock()
    env_dir = project.prepare()

    assert project.environments["standard"].lockfile.samefile(
        project_path / "standard.conda-lock.yml"
    )
    assert project.environments["standard"].prefix.samefile(
        project_path / "envs" / "standard"
    )

    assert env_dir.samefile(project_path / "envs" / "standard")

    conda_history = env_dir / "conda-meta" / "history"
    assert conda_history.exists()


def test_lock_and_prepare_env_by_name(project_directory_factory):
    env_yaml = """dependencies: []
"""

    project_yaml = f"""name: test
environments:
  standard: [environment{project_directory_factory._suffix}]
"""

    project_path = project_directory_factory(
        env_yaml=env_yaml, project_yaml=project_yaml
    )
    project = CondaProject(project_path)
    project.lock(environment="standard")
    env_dir = project.prepare(environment="standard")

    assert project.environments["standard"].lockfile.samefile(
        project_path / "standard.conda-lock.yml"
    )
    assert project.environments["standard"].prefix.samefile(
        project_path / "envs" / "standard"
    )

    assert env_dir.samefile(project_path / "envs" / "standard")

    conda_history = env_dir / "conda-meta" / "history"
    assert conda_history.exists()


def test_lock_and_prepare_env_by_object(project_directory_factory):
    env_yaml = """dependencies: []
"""

    project_yaml = f"""name: test
environments:
  standard: [environment{project_directory_factory._suffix}]
"""

    project_path = project_directory_factory(
        env_yaml=env_yaml, project_yaml=project_yaml
    )
    project = CondaProject(project_path)
    project.lock(environment=project.environments["standard"])
    env_dir = project.prepare(environment=project.environments["standard"])

    assert project.environments["standard"].lockfile.samefile(
        project_path / "standard.conda-lock.yml"
    )
    assert project.environments["standard"].prefix.samefile(
        project_path / "envs" / "standard"
    )

    assert env_dir.samefile(project_path / "envs" / "standard")

    conda_history = env_dir / "conda-meta" / "history"
    assert conda_history.exists()


def test_project_non_environment_yaml_name(project_directory_factory):
    env_yaml = """dependencies: []
"""

    project_yaml = f"""name: test
environments:
  standard: [env{project_directory_factory._suffix}]
"""

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={f"env{project_directory_factory._suffix}": env_yaml},
    )
    project = CondaProject(project_path)

    assert project.default_environment.sources[0].samefile(
        (project_path / "env").with_suffix(project_directory_factory._suffix)
    )


def test_lock_and_prepare_non_environment_yaml_name(project_directory_factory):
    env_yaml = """dependencies: []
"""

    project_yaml = f"""name: test
environments:
  standard: [env{project_directory_factory._suffix}]
"""

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={f"env{project_directory_factory._suffix}": env_yaml},
    )
    project = CondaProject(project_path)
    project.lock()
    project.prepare()

    assert project.default_environment.lockfile.exists()

    with project.default_environment.lockfile.open() as f:
        lock = YAML().load(f)

    assert lock["metadata"]["sources"][0] == str(project.default_environment.sources[0])

    assert (project.default_environment.prefix / "conda-meta" / "history").exists()
