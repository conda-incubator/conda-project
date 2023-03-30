# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
from textwrap import dedent

import pytest

from conda_project.exceptions import CommandNotFoundError
from conda_project.project import CondaProject


@pytest.fixture
def one_env_no_commands(project_directory_factory) -> CondaProject:
    env_yaml = "dependencies: []\n"

    project_yaml = dedent(
        f"""\
        name: test
        environments:
          default: [environment{project_directory_factory._suffix}]
        commands: {{}}
        """
    )

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"environment{project_directory_factory._suffix}": env_yaml,
        },
    )
    project = CondaProject(project_path)
    return project


@pytest.fixture
def one_env_one_command(project_directory_factory) -> CondaProject:
    env_yaml = "dependencies: []\n"
    project_yaml = dedent(
        f"""\
        name: test
        environments:
          default: [environment{project_directory_factory._suffix}]
        commands:
          the-command: run-me
        """
    )

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"environment{project_directory_factory._suffix}": env_yaml,
        },
    )
    project = CondaProject(project_path)
    return project


@pytest.fixture
def one_env_one_command_project_variable(project_directory_factory) -> CondaProject:
    env_yaml = "dependencies: []\n"
    project_yaml = dedent(
        f"""\
        name: test
        environments:
          default: [environment{project_directory_factory._suffix}]
        commands:
          the-command: run-me
        variables:
          FOO: set-in-project
        """
    )

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"environment{project_directory_factory._suffix}": env_yaml,
        },
    )
    project = CondaProject(project_path)
    return project


@pytest.fixture
def one_env_one_command_command_variable(project_directory_factory) -> CondaProject:
    env_yaml = "dependencies: []\n"
    project_yaml = dedent(
        f"""\
        name: test
        environments:
          default: [environment{project_directory_factory._suffix}]
        commands:
          the-command:
            cmd: run-me
            variables:
              FOO: set-in-command
        """
    )

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"environment{project_directory_factory._suffix}": env_yaml,
        },
    )
    project = CondaProject(project_path)
    return project


@pytest.fixture
def one_env_one_command_project_variable_overridden(
    project_directory_factory,
) -> CondaProject:
    env_yaml = "dependencies: []\n"
    project_yaml = dedent(
        f"""\
        name: test
        environments:
          default: [environment{project_directory_factory._suffix}]
        variables:
          FOO: set-in-project
        commands:
          the-command:
            cmd: run-me
            variables:
              FOO: set-in-command
        """
    )

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"environment{project_directory_factory._suffix}": env_yaml,
        },
    )
    project = CondaProject(project_path)
    return project


@pytest.fixture
def multi_env_multi_command(project_directory_factory):
    env1 = env2 = "dependencies: []\n"
    project_yaml = dedent(
        f"""\
        name: multi-envs
        environments:
          env1: [env1{project_directory_factory._suffix}]
          env2: [env2{project_directory_factory._suffix}]
        commands:
          cmd1:
            cmd: 'run-me1'
            environment: env1
          cmd2:
            cmd: 'run-me2'
            environment: env2
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
    return project


def test_raise_command_not_found(one_env_no_commands: CondaProject):
    project = one_env_no_commands

    with pytest.raises(CommandNotFoundError):
        project.default_command.run()

    with pytest.raises(CommandNotFoundError):
        project.commands["the-command"].run()


def test_run_default_command_after_lock_and_install(
    one_env_one_command: CondaProject, mocked_execvped, mocker
):
    from conda_project import project as project_module

    conda_run = mocker.spy(project_module, "conda_run")

    project = one_env_one_command
    assert not project.default_environment.is_locked
    assert not project.default_environment.is_consistent

    project.default_command.run()

    assert project.default_environment.is_locked
    assert project.default_environment.is_consistent

    assert mocked_execvped.call_count == 1
    assert conda_run.call_args == mocker.call(
        cmd="run-me",
        prefix=project.default_environment.prefix,
        working_dir=project.directory,
        env=os.environ,
        extra_args=None,
    )


def test_run_command_by_name(
    one_env_one_command: CondaProject, mocked_execvped, mocker
):
    from conda_project import project as project_module

    conda_run = mocker.spy(project_module, "conda_run")

    project = one_env_one_command

    project.commands["the-command"].run()

    assert mocked_execvped.call_count == 1
    assert conda_run.call_args == mocker.call(
        cmd="run-me",
        prefix=project.default_environment.prefix,
        working_dir=project.directory,
        env=os.environ,
        extra_args=None,
    )


def test_run_with_project_variable(
    one_env_one_command_project_variable: CondaProject, mocked_execvped, mocker
):
    from conda_project import project as project_module

    conda_run = mocker.spy(project_module, "conda_run")
    prepare_variables = mocker.spy(project_module, "prepare_variables")

    project = one_env_one_command_project_variable

    project.commands["the-command"].run()

    assert prepare_variables.call_args == mocker.call(
        project.directory, {"FOO": "set-in-project"}, None
    )

    env = conda_run.call_args.kwargs["env"]
    assert env.get("FOO") == "set-in-project"

    assert mocked_execvped.call_count == 1


def test_run_with_command_variable(
    one_env_one_command_command_variable: CondaProject, mocked_execvped, mocker
):
    from conda_project import project as project_module

    conda_run = mocker.spy(project_module, "conda_run")
    prepare_variables = mocker.spy(project_module, "prepare_variables")

    project = one_env_one_command_command_variable

    project.commands["the-command"].run()

    assert prepare_variables.call_args == mocker.call(
        project.directory, {}, {"FOO": "set-in-command"}
    )

    env = conda_run.call_args.kwargs["env"]
    assert env.get("FOO") == "set-in-command"

    assert mocked_execvped.call_count == 1


def test_run_with_project_variable_overriden(
    one_env_one_command_project_variable_overridden: CondaProject,
    mocked_execvped,
    mocker,
):
    from conda_project import project as project_module

    conda_run = mocker.spy(project_module, "conda_run")
    prepare_variables = mocker.spy(project_module, "prepare_variables")

    project = one_env_one_command_project_variable_overridden

    project.commands["the-command"].run()

    assert prepare_variables.call_args == mocker.call(
        project.directory, {"FOO": "set-in-project"}, {"FOO": "set-in-command"}
    )

    env = conda_run.call_args.kwargs["env"]
    assert env.get("FOO") == "set-in-command"

    assert mocked_execvped.call_count == 1


def test_run_with_defined_env(
    multi_env_multi_command: CondaProject, mocked_execvped, mocker
):
    from conda_project import project as project_module

    conda_run = mocker.spy(project_module, "conda_run")

    project = multi_env_multi_command

    project.commands["cmd1"].run()

    environment = conda_run.call_args.kwargs["prefix"]
    assert environment == project.environments["env1"].prefix

    assert mocked_execvped.call_count == 1


def test_run_with_other_env(
    multi_env_multi_command: CondaProject, mocked_execvped, mocker
):
    from conda_project import project as project_module

    conda_run = mocker.spy(project_module, "conda_run")

    project = multi_env_multi_command

    project.commands["cmd1"].run(environment="env2")

    environment = conda_run.call_args.kwargs["prefix"]
    assert environment == project.environments["env2"].prefix

    assert mocked_execvped.call_count == 1


def test_run_all_commands(
    multi_env_multi_command: CondaProject, mocked_execvped, mocker
):
    from conda_project import project as project_module

    conda_run = mocker.spy(project_module, "conda_run")

    project = multi_env_multi_command

    assert "cmd1" in project.commands.keys()
    assert "cmd2" in project.commands.keys()

    for cmd in project.commands.values():
        cmd.run()

    assert conda_run.call_count == 2
    assert mocked_execvped.call_count == 2


def test_run_with_extra_args(
    one_env_one_command: CondaProject, mocked_execvped, mocker
):
    from conda_project import project as project_module

    conda_run = mocker.spy(project_module, "conda_run")

    project = one_env_one_command

    project.default_command.run(extra_args=["--flag", "a", "b"])

    assert mocked_execvped.call_count == 1
    assert conda_run.call_args == mocker.call(
        cmd="run-me",
        prefix=project.default_environment.prefix,
        working_dir=project.directory,
        env=os.environ,
        extra_args=["--flag", "a", "b"],
    )


def test_activate_prepares_env(one_env_no_commands: CondaProject, mocker):
    mocker.patch("conda_project.project.conda_activate")

    project = one_env_no_commands

    assert not project.default_environment.is_consistent

    project.default_environment.activate()

    assert project.default_environment.is_consistent


def test_activate_with_env_vars(
    one_env_one_command_project_variable: CondaProject, mocker
):
    mocked_activate = mocker.patch("conda_project.project.conda_activate")

    project = one_env_one_command_project_variable

    project.default_environment.activate()

    assert mocked_activate.call_args.kwargs["env"].get("FOO") == "set-in-project"
