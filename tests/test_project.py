# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
import logging
import os
from pathlib import Path
from textwrap import dedent

import pytest
from ruamel.yaml import YAML

from conda_project.conda import call_conda
from conda_project.exceptions import CondaProjectError, CondaProjectLockFailed
from conda_project.project import DEFAULT_PLATFORMS, CondaProject


def is_libmamba_installed():
    proc = call_conda(["list", "-n", "base", "conda-libmamba-solver", "--json"])
    result = json.loads(proc.stdout)
    if result:
        return result[0]["name"] == "conda-libmamba-solver"
    else:
        return False


def test_project_create_new_directory(tmp_path, capsys):
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


def test_project_create_twice(tmp_path, capsys):
    _ = CondaProject.init(tmp_path, lock_dependencies=False)
    p = CondaProject.init(tmp_path, lock_dependencies=False, verbose=True)

    out, _ = capsys.readouterr()
    assert f"Existing project file found at {p.project_yaml_path}.\n" == out


def test_project_create_default_platforms(tmp_path):
    p = CondaProject.init(tmp_path, lock_dependencies=False)

    with p.default_environment.sources[0].open() as f:
        env = YAML().load(f)

    assert env["platforms"] == list(DEFAULT_PLATFORMS)


def test_project_create_specific_platforms(tmp_path):
    p = CondaProject.init(tmp_path, platforms=["linux-64"], lock_dependencies=False)

    with p.default_environment.sources[0].open() as f:
        env = YAML().load(f)

    assert env["platforms"] == ["linux-64"]


def test_project_create_specific_channels(tmp_path):
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


def test_project_create_default_channel(tmp_path):
    p = CondaProject.init(
        tmp_path, dependencies=["python=3.8", "numpy"], lock_dependencies=False
    )

    with p.default_environment.sources[0].open() as f:
        env = YAML().load(f)

    assert env["dependencies"] == ["python=3.8", "numpy"]
    assert env["channels"] == ["defaults"]


def test_project_create_conda_configs(tmp_path):
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
def test_project_create_and_lock(tmp_path):
    p = CondaProject.init(tmp_path, dependencies=["python=3.8"], lock_dependencies=True)
    assert p.default_environment.lockfile.exists()
    assert p.default_environment.lockfile == tmp_path / "conda-lock.default.yml"


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
    env_yaml = dedent(
        """\
        name: test
        dependencies: []
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    env_dir = project.default_environment.install()
    assert (env_dir / ".gitignore").exists()
    with (env_dir / ".gitignore").open("rt") as f:
        assert f.read().strip() == "*"


def test_prepare_no_dependencies(project_directory_factory):
    env_yaml = dedent(
        """\
        name: test
        dependencies: []
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    env_dir = project.default_environment.install()
    assert env_dir.samefile(project_path / "envs" / "default")

    conda_history = env_dir / "conda-meta" / "history"
    assert conda_history.exists()
    assert project.default_environment.is_consistent


@pytest.mark.slow
def test_is_prepared(project_directory_factory):
    env_yaml = dedent(
        """\
        name: test
        dependencies: [python=3.8]
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    _ = project.default_environment.install()
    assert project.default_environment.is_consistent

    updated_yaml = dedent(
        """\
        name: test
        dependencies:
          - python=3.8
          - requests
        """
    )

    with (project.default_environment.sources[0]).open("wt") as f:
        f.write(updated_yaml)

    assert not project.default_environment.is_locked
    assert not project.default_environment.is_consistent

    _ = project.default_environment.install(force=False)
    assert project.default_environment.is_locked
    assert not project.default_environment.is_consistent

    _ = project.default_environment.install(force=True)
    assert project.default_environment.is_consistent


@pytest.mark.slow
def test_is_prepared_with_pip_package(project_directory_factory):
    """Test that we can import the package if it is installed with pip."""
    env_yaml = dedent(
        """\
        name: test
        dependencies:
          - python=3.8
          - pip
          - pip:
            - requests
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    _ = project.default_environment.install()

    # This assertion won't pass if there are pip packages
    assert project.default_environment.is_consistent

    args = [
        "run",
        *("-p", str(project.environments["default"].prefix)),
        "python",
        *("-c", "import requests"),
    ]
    result = call_conda(args, condarc_path=project.condarc)
    assert result.returncode == 0


@pytest.mark.slow
def test_is_prepared_live_env_changed(project_directory_factory, capsys):
    env_yaml = dedent(
        """\
        name: test
        dependencies: [python=3.8]
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    _ = project.default_environment.install()
    assert project.default_environment.is_locked
    assert project.default_environment.is_consistent

    _ = call_conda(
        ["install", "-p", str(project.default_environment.prefix), "requests", "-y"]
    )

    assert project.default_environment.is_locked
    assert not project.default_environment.is_consistent

    _ = project.default_environment.install(force=False, verbose=True)
    assert not project.default_environment.is_consistent

    stdout = capsys.readouterr().out
    assert "The environment exists but does not match the locked dependencies" in stdout


@pytest.mark.slow
def test_is_prepared_source_changed(project_directory_factory, capsys):
    env_yaml = dedent(
        """\
        name: test
        dependencies: [python=3.8]
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    _ = project.default_environment.install()
    assert project.default_environment.is_locked
    assert project.default_environment.is_consistent

    _ = call_conda(
        ["install", "-p", str(project.default_environment.prefix), "requests", "-y"]
    )

    assert project.default_environment.is_locked
    assert not project.default_environment.is_consistent

    _ = project.default_environment.install(force=False, verbose=True)
    assert not project.default_environment.is_consistent

    stdout = capsys.readouterr().out
    assert "The environment exists but does not match the locked dependencies" in stdout


def test_install_env_exists(project_directory_factory, capsys):
    env_yaml = dedent(
        """\
        name: test
        dependencies: []
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    env_dir = project.default_environment.install(verbose=True)

    stdout = capsys.readouterr().out
    assert f"environment created at {env_dir}" in stdout

    _ = project.default_environment.install(verbose=True)

    stdout = capsys.readouterr().out
    assert "The environment already exists" in stdout


@pytest.mark.slow
def test_install_and_clean(project_directory_factory):
    env_yaml = dedent(
        """\
        name: test
        dependencies:
          - python=3.8
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
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
        """\
        name: test
        dependencies:
          - python=3.8
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock()

    lockfile = project_path / "conda-lock.default.yml"
    assert lockfile == project.default_environment.lockfile
    assert lockfile.exists()
    assert project.default_environment.is_locked


def test_lock_no_channels(project_directory_factory):
    env_yaml = dedent(
        """\
        name: test
        dependencies: []
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
        """\
        name: test
        channels: [defusco, conda-forge, defaults]
        dependencies: []
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


def test_lock_wrong_platform(project_directory_factory):
    env_yaml = dedent(
        """\
        name: test
        dependencies: []
        platforms: [dummy-platform]
        """
    )

    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock()
    assert project.default_environment.is_locked

    with pytest.raises(CondaProjectError) as e:
        project.default_environment.install()
    assert "not in the supported locked platforms" in str(e.value)


def test_install_as_platform(project_directory_factory):
    env_yaml = dedent(
        """\
        name: test
        dependencies: []
        platforms: [dummy-platform]
        """
    )

    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock()
    assert project.default_environment.is_locked

    project.default_environment.install(as_platform="dummy-platform")

    with project.default_environment.prefix / "condarc" as f:
        env_condarc = YAML().load(f)

    assert env_condarc["subdir"] == "dummy-platform"

    project.default_environment.install(force=True)

    with project.default_environment.prefix / "condarc" as f:
        env_condarc = YAML().load(f)

    assert env_condarc["subdir"] == "dummy-platform"


def test_force_relock(project_directory_factory, capsys):
    env_yaml = dedent(
        """\
        name: test
        dependencies: []
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
        """\
        name: test
        dependencies: []
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock(verbose=True)
    assert project.default_environment.is_locked

    updated_env_yaml = dedent(
        """\
        name: test
        dependencies:
          - python=3.8
        """
    )
    with (project.default_environment.sources[0]).open("wt") as f:
        f.write(updated_env_yaml)

    assert not project.default_environment.is_locked


@pytest.mark.slow
def test_relock_add_packages(project_directory_factory):
    env_yaml = dedent(
        """\
        name: test
        dependencies:
          - python=3.8
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
        """\
        name: test
        dependencies:
          - python=3.8
          - requests
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
        """\
        name: test
        dependencies:
          - python=3.8
          - requests
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
        """\
        name: test
        dependencies:
          - python=3.8
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
        """\
        name: test
        dependencies:
          - python=3.8
          - requests
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
        """\
        name: test
        dependencies:
          - python=3.8
          - _bad-package-8933
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


def test_install_relocks(project_directory_factory, capsys):
    env_yaml = dedent(
        """\
        name: test
        dependencies: []
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)

    project = CondaProject(project_path)
    project.default_environment.lock(verbose=True)
    assert project.default_environment.is_locked

    updated_env_yaml = dedent(
        """\
        name: test
        dependencies:
          - python=3.8
        """
    )
    with (project.default_environment.sources[0]).open("wt") as f:
        f.write(updated_env_yaml)

    project.default_environment.install(verbose=True, force=True)

    assert "is out-of-date, re-locking" in capsys.readouterr().out


def test_project_named_environment(project_directory_factory):
    env_yaml = "dependencies: []\n"

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


def test_project_hyphen_named_environment(project_directory_factory):
    env_yaml = "dependencies: []\n"

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


def test_install_named_environment(project_directory_factory):
    env_yaml = "dependencies: []\n"

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
    project.default_environment.lock()
    env_dir = project.default_environment.install()

    assert project.environments["standard"].lockfile.samefile(
        project_path / "conda-lock.standard.yml"
    )
    assert project.environments["standard"].prefix.samefile(
        project_path / "envs" / "standard"
    )

    assert env_dir.samefile(project_path / "envs" / "standard")

    conda_history = env_dir / "conda-meta" / "history"
    assert conda_history.exists()


def test_project_environments_immutable(project_directory_factory):
    env_yaml = "dependencies: []\n"

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
    env_yaml = "dependencies: []\n"

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
    env_yaml = "dependencies: []\n"

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
    env_yaml = "dependencies: []\n"

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
    env_yaml = "dependencies: []\n"

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
    environment_yml = "dependencies: [python]\n"

    extras_yml = "dependencies: [requests]\n"

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
        str(project_path / f"environment{project_directory_factory._suffix}"),
        str(project_path / f"extras{project_directory_factory._suffix}"),
    ]

    assert "requests" in [p["name"] for p in lock["package"]]
    assert "python" in [p["name"] for p in lock["package"]]


@pytest.mark.slow
def test_project_lock_env_multiple_sources_different_directories(
    project_directory_factory,
):
    environment_yml = "dependencies: [python]\n"

    extras_yml = "dependencies: [requests]\n"

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

    assert Path(lock["metadata"]["sources"][0]).samefile(
        project_path / "project" / f"environment{project_directory_factory._suffix}"
    )
    assert Path(lock["metadata"]["sources"][1]).samefile(
        project_path / f"extras{project_directory_factory._suffix}"
    )

    assert "requests" in [p["name"] for p in lock["package"]]
    assert "python" in [p["name"] for p in lock["package"]]


@pytest.mark.skipif(
    not is_libmamba_installed(), reason="Libmamba solver not installed."
)
def test_failed_to_solve_libmamba(project_directory_factory):
    env_yaml = dedent(
        """\
        name: fail
        channels:
          - conda-forge

        dependencies:
          - ensureconda
          - conda-token
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
        """\
        name: fail
        channels:
          - conda-forge

        dependencies:
          - ensureconda
          - conda-token
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
    env1 = env2 = "dependencies: []\n"
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

    env1 = "dependencies: [python=3.8]\n"
    with (project_path / f"env1{project_directory_factory._suffix}").open("w") as f:
        f.write(env1)

    assert not project.check(verbose=True)

    assert "is out-of-date" in capsys.readouterr().err
