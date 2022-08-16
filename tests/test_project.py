# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os

import logging
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
    assert not p.default_environment.is_locked

    assert p.condarc.exists()
    with p.condarc.open() as f:
        condarc = YAML().load(f)
    assert condarc == {}

    out, _ = capsys.readouterr()
    assert f"Project created at {project_directory}\n" == out


def test_project_create_twice(tmpdir, capsys):
    _ = CondaProject.create(tmpdir, lock_dependencies=False)
    p = CondaProject.create(tmpdir, lock_dependencies=False, verbose=True)

    out, _ = capsys.readouterr()
    assert f"Existing project file found at {p.project_yaml_path}.\n" == out


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

    for path in [p.condarc, p.default_environment.condarc]:
        with path.open() as f:
            condarc = YAML().load(f)

        assert condarc["experimental_solver"] == "libmamba"


@pytest.mark.slow
def test_project_create_and_lock(tmpdir):
    p = CondaProject.create(tmpdir, dependencies=["python=3.8"], lock_dependencies=True)
    assert p.default_environment.lockfile.exists()
    assert p.default_environment.lockfile == Path(tmpdir) / "default.conda-lock.yml"


def test_conda_project_init_empty_dir(tmpdir, caplog):
    caplog.set_level(logging.INFO)

    with pytest.raises(CondaProjectError) as excinfo:
        CondaProject(tmpdir)
    assert "No Conda environment.yml or environment.yaml file was found" in str(
        excinfo.value
    )

    assert "No conda-project.yml or conda-project.yaml file was found" in caplog.text


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
    assert project.default_environment.sources == (
        (project.directory / "environment").with_suffix(
            project_directory_factory._suffix
        ),
    )
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


def test_prepare_with_gitignore(project_directory_factory):
    env_yaml = """name: test
dependencies: []
"""
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    env_dir = project.default_environment.prepare()
    assert (env_dir / ".gitignore").exists()


def test_prepare_no_dependencies(project_directory_factory):
    env_yaml = """name: test
dependencies: []
"""
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    env_dir = project.default_environment.prepare()
    assert env_dir.samefile(project_path / "envs" / "default")

    conda_history = env_dir / "conda-meta" / "history"
    assert conda_history.exists()
    assert project.default_environment.is_prepared


def test_prepare_env_exists(project_directory_factory, capsys):
    env_yaml = """name: test
dependencies: []
"""
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    env_dir = project.default_environment.prepare(verbose=True)

    out, _ = capsys.readouterr()
    assert f"environment created at {env_dir}" == out.splitlines()[-1]

    _ = project.default_environment.prepare(verbose=True)

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
    env_dir = project.default_environment.prepare()
    assert env_dir.samefile(project_path / "envs" / "default")

    conda_history = env_dir / "conda-meta" / "history"
    assert conda_history.exists()

    with conda_history.open() as f:
        assert "create -y --file" in f.read()
    conda_history_mtime = os.path.getmtime(conda_history)

    project.default_environment.prepare()
    assert conda_history_mtime == os.path.getmtime(conda_history)

    project.default_environment.prepare(force=True)
    assert conda_history_mtime < os.path.getmtime(conda_history)

    project.default_environment.clean()
    assert not conda_history.exists()
    assert not project.default_environment.is_prepared


@pytest.mark.slow
def test_lock(project_directory_factory):
    env_yaml = """name: test
dependencies:
  - python=3.8
"""
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock()

    lockfile = project_path / "default.conda-lock.yml"
    assert lockfile == project.default_environment.lockfile
    assert lockfile.exists()
    assert project.default_environment.is_locked


def test_lock_no_channels(project_directory_factory):
    env_yaml = """name: test
dependencies: []
"""
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)

    with pytest.warns(UserWarning, match=r"there are no 'channels:' key.*"):
        project.default_environment.lock(verbose=True)

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
    project.default_environment.lock()

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
    project.default_environment.lock()

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
    project.default_environment.lock(verbose=True)

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
    project.default_environment.lock()
    assert project.default_environment.is_locked

    with pytest.raises(CondaProjectError) as e:
        project.default_environment.prepare()
    assert "not in the supported locked platforms" in str(e.value)


def test_force_relock(project_directory_factory, capsys):
    env_yaml = """name: test
dependencies: []
"""
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock(verbose=True)
    assert project.default_environment.is_locked

    lockfile_mtime = os.path.getmtime(project.default_environment.lockfile)
    project.default_environment.lock(verbose=True)
    assert "Skipping" in capsys.readouterr().out.splitlines()[-2]
    assert lockfile_mtime == os.path.getmtime(project.default_environment.lockfile)

    project.default_environment.lock(force=True)
    assert lockfile_mtime < os.path.getmtime(project.default_environment.lockfile)


def test_lock_outdated(project_directory_factory):
    env_yaml = """name: test
dependencies: []
"""
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock(verbose=True)
    assert project.default_environment.is_locked

    updated_env_yaml = """name: test
dependencies:
  - python=3.8
"""
    with (project.default_environment.sources[0]).open("wt") as f:
        f.write(updated_env_yaml)

    assert not project.default_environment.is_locked


@pytest.mark.slow
def test_update_lock(project_directory_factory):
    env_yaml = """name: test
dependencies: []
"""
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock(verbose=True)
    assert project.default_environment.is_locked

    updated_env_yaml = """name: test
dependencies:
  - python=3.8
"""
    with (project.default_environment.sources[0]).open("wt") as f:
        f.write(updated_env_yaml)

    assert not project.default_environment.is_locked

    project.default_environment.lock()
    with project.default_environment.lockfile.open() as f:
        y = YAML().load(f)

    assert "python" in [p["name"] for p in y["package"]]


@pytest.mark.slow
def test_relock_add_packages(project_directory_factory):
    env_yaml = """name: test
dependencies:
  - python=3.8
"""
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock()

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

    project.default_environment.lock()
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


def test_project_hyphen_renamed_environment(project_directory_factory):
    env_yaml = """dependencies: []
"""

    project_yaml = f"""name: test
environments:
  my-env: [environment{project_directory_factory._suffix}]
"""

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
    project.default_environment.lock()
    env_dir = project.default_environment.prepare()

    assert project.environments["standard"].lockfile.samefile(
        project_path / "standard.conda-lock.yml"
    )
    assert project.environments["standard"].prefix.samefile(
        project_path / "envs" / "standard"
    )

    assert env_dir.samefile(project_path / "envs" / "standard")

    conda_history = env_dir / "conda-meta" / "history"
    assert conda_history.exists()


def test_project_environments_immutable(project_directory_factory):
    env_yaml = """dependencies: []
"""

    project_yaml = f"""name: test
environments:
  default: [env{project_directory_factory._suffix}]
"""

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
    env_yaml = """dependencies: []
"""

    project_yaml = f"""name: test
environments:
  bbb: [env1{project_directory_factory._suffix}]
  default: [env2{project_directory_factory._suffix}]
"""

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


def test_lock_prepare_clean_default_with_multiple_envs(project_directory_factory):
    env_yaml = """dependencies: []
"""

    project_yaml = f"""name: test
environments:
  bbb: [env1{project_directory_factory._suffix}]
  default: [env2{project_directory_factory._suffix}]
"""

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"env1{project_directory_factory._suffix}": env_yaml,
            f"env2{project_directory_factory._suffix}": env_yaml,
        },
    )
    project = CondaProject(project_path)
    project.default_environment.lock()
    project.default_environment.prepare()

    assert project.default_environment.lockfile.samefile(
        project_path / "bbb.conda-lock.yml"
    )
    assert project.default_environment.lockfile.exists()

    assert project.default_environment.prefix.samefile(project_path / "envs" / "bbb")
    assert (project.default_environment.prefix / "conda-meta" / "history").exists()

    project.default_environment.clean()
    assert not project.default_environment.prefix.exists()


def test_lock_prepare_clean_named_with_multiple_envs(project_directory_factory):
    env_yaml = """dependencies: []
"""

    project_yaml = f"""name: test
environments:
  bbb: [env1{project_directory_factory._suffix}]
  default: [env2{project_directory_factory._suffix}]
"""

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"env1{project_directory_factory._suffix}": env_yaml,
            f"env2{project_directory_factory._suffix}": env_yaml,
        },
    )
    project = CondaProject(project_path)
    project.environments["default"].lock()
    project.environments["default"].prepare()

    assert project.environments["default"].lockfile.samefile(
        project_path / "default.conda-lock.yml"
    )
    assert project.environments["default"].lockfile.exists()

    assert project.environments["default"].prefix.samefile(
        project_path / "envs" / "default"
    )
    assert (project.environments["default"].prefix / "conda-meta" / "history").exists()

    project.environments["default"].clean()
    assert not project.environments["default"].prefix.exists()


def test_lock_prepare_clean_multiple_envs(project_directory_factory):
    env_yaml = """dependencies: []
"""

    project_yaml = f"""name: test
environments:
  bbb: [env1{project_directory_factory._suffix}]
  default: [env2{project_directory_factory._suffix}]
"""

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"env1{project_directory_factory._suffix}": env_yaml,
            f"env2{project_directory_factory._suffix}": env_yaml,
        },
    )
    project = CondaProject(project_path)

    project.environments["bbb"].lock()
    project.environments["bbb"].prepare()

    assert project.environments["bbb"].lockfile.samefile(
        project_path / "bbb.conda-lock.yml"
    )
    assert project.environments["bbb"].lockfile.exists()

    assert project.environments["bbb"].prefix.samefile(project_path / "envs" / "bbb")
    assert (project.environments["bbb"].prefix / "conda-meta" / "history").exists()

    project.environments["default"].lock()
    project.environments["default"].prepare()

    assert project.environments["default"].lockfile.samefile(
        project_path / "default.conda-lock.yml"
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
    environment_yml = """dependencies: [python]
"""

    extras_yml = """dependencies: [requests]
"""

    project_yaml = f"""name: test
environments:
  default:
    - environment{project_directory_factory._suffix}
    - extras{project_directory_factory._suffix}
"""

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
        str(project_path / f"environment{project_directory_factory._suffix}"),
        str(project_path / f"extras{project_directory_factory._suffix}"),
    ]

    assert "requests" in [p["name"] for p in lock["package"]]
    assert "python" in [p["name"] for p in lock["package"]]


@pytest.mark.slow
def test_project_lock_env_multiple_sources_different_directories(
    project_directory_factory,
):
    environment_yml = """dependencies: [python]
"""

    extras_yml = """dependencies: [requests]
"""

    project_yaml = f"""name: test
environments:
  default:
    - ./environment{project_directory_factory._suffix}
    - ../extras{project_directory_factory._suffix}
"""

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

    assert Path(lock["metadata"]["sources"][0]).samefile(
        project_path / "project" / f"environment{project_directory_factory._suffix}"
    )
    assert Path(lock["metadata"]["sources"][1]).samefile(
        project_path / f"extras{project_directory_factory._suffix}"
    )

    assert "requests" in [p["name"] for p in lock["package"]]
    assert "python" in [p["name"] for p in lock["package"]]


def test_failed_to_solve_libmamba(project_directory_factory):
    env_yaml = """name: fail
channels:
  - conda-forge

dependencies:
  - ensureconda
  - conda-token
"""

    condarc = "experimental_solver: libmamba"

    project_path = project_directory_factory(
        env_yaml=env_yaml, files={".condarc": condarc}
    )
    project = CondaProject(project_path)

    with pytest.raises(CondaProjectError) as exinfo:
        project.default_environment.lock()

    assert "The following packages are missing from the supplied channels" in str(
        exinfo.value
    )


def test_failed_to_solve_classic(project_directory_factory):
    env_yaml = """name: fail
channels:
  - conda-forge

dependencies:
  - ensureconda
  - conda-token
"""
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
