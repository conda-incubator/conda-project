# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from textwrap import dedent

import pytest
from ruamel.yaml import YAML

from conda_project.conda import call_conda
from conda_project.exceptions import CondaProjectError
from conda_project.project import CondaProject


def test_install_with_gitignore(project_directory_factory):
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


def test_install_no_dependencies(project_directory_factory):
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
def test_is_installed(project_directory_factory):
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
def test_is_installed_with_pip_package(project_directory_factory):
    """Test that we can import the package if it is installed with pip."""
    env_yaml = dedent(
        """\
        name: test
        dependencies:
          - python=3.8
          - pip
          - pip:
            - requests
            - pyrfc3339 # this becomes 'pyRFC3339' in pip freeze
        """
    )
    project_path = project_directory_factory(env_yaml=env_yaml)
    project = CondaProject(project_path)

    _ = project.default_environment.install()

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
