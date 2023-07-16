# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import json

import pytest
from pytest_mock import MockerFixture

from conda_project.conda import call_conda
from conda_project.exceptions import CondaProjectLockFailed
from conda_project.project import CondaProject
from conda_project.project_file import EnvironmentYaml


def test_add_nothing(project: CondaProject):
    project.default_environment.add(dependencies=[])

    assert not project.default_environment.is_locked
    assert not project.default_environment.is_consistent


def test_remove_from_empty(project: CondaProject):
    project.default_environment.remove(dependencies=[])

    env = EnvironmentYaml.parse_yaml(project.default_environment.sources[0])
    assert env.dependencies == []

    assert not project.default_environment.is_locked
    assert not project.default_environment.is_consistent


def test_remove_undefined_dependency(project: CondaProject):
    project.default_environment.remove(
        dependencies=["this-package-is-not-already-installed"]
    )

    env = EnvironmentYaml.parse_yaml(project.default_environment.sources[0])
    assert env.dependencies == []

    assert not project.default_environment.is_locked
    assert not project.default_environment.is_consistent


def test_add_invalid_dependency(project: CondaProject):
    original_env = EnvironmentYaml.parse_yaml(project.default_environment.sources[0])

    with pytest.raises(CondaProjectLockFailed):
        project.default_environment.add(
            dependencies=["fake-channel:nope:__fake-package__"]
        )

    env = EnvironmentYaml.parse_yaml(project.default_environment.sources[0])
    assert env.dependencies == original_env.dependencies

    assert not project.default_environment.is_locked
    assert not project.default_environment.is_consistent


@pytest.mark.slow
def test_add_and_remove(project: CondaProject, mocker: MockerFixture):
    from conda_project.project import Environment

    install_spy = mocker.spy(Environment, "install")

    assert not project.default_environment.lockfile.exists()
    assert not project.default_environment.is_consistent

    project.default_environment.add(
        dependencies=["python=3.10", "requests"], channels=["defaults"]
    )

    env = EnvironmentYaml.parse_yaml(project.default_environment.sources[0])
    assert env.dependencies == ["python=3.10", "requests"]

    assert project.default_environment.lockfile.exists()
    assert project.default_environment.is_locked
    assert project.default_environment.is_consistent
    assert install_spy.call_args_list[-1].kwargs["force"] is True

    proc = call_conda(["list", "-p", str(project.default_environment.prefix), "--json"])
    pkgs = json.loads(proc.stdout)
    names = sorted(p["name"] for p in pkgs)
    assert "python" in names
    assert "requests" in names

    project.default_environment.remove(dependencies=["requests"])

    env = EnvironmentYaml.parse_yaml(project.default_environment.sources[0])
    assert env.dependencies == ["python=3.10"]

    assert project.default_environment.lockfile.exists()
    assert project.default_environment.is_consistent

    proc = call_conda(["list", "-p", str(project.default_environment.prefix), "--json"])
    pkgs = json.loads(proc.stdout)
    names = sorted(p["name"] for p in pkgs)
    assert "python" in names
    assert "requests" not in names
