# -*- coding: utf-8 -*-
# Copyright (C) 2022-2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from argparse import Namespace
from textwrap import dedent

import pytest
from pytest_mock import MockFixture

from conda_project.cli.commands import _get_environment_from_args, _load_project
from conda_project.cli.main import cli, main, parse_and_run
from conda_project.exceptions import CondaProjectError
from conda_project.project import CondaProject, current_platform

PROJECT_ACTIONS = ("init", "create", "check")
ENVIRONMENT_ACTIONS = (
    "clean",
    "install",
    "prepare",
    "lock",
    "activate",
)
DEPENDENCIES_ACTIONS = (
    "add",
    "remove",
)
COMMAND_ACTIONS = ("run",)
ALL_ACTIONS = (
    PROJECT_ACTIONS + DEPENDENCIES_ACTIONS + ENVIRONMENT_ACTIONS + COMMAND_ACTIONS
)


@pytest.fixture
def multi_env(project_directory_factory):
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

    return project_path


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
            cmd: ''
            environment: env1
          cmd2:
            cmd: ''
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

    return project_path


def test_known_actions():
    parser = cli()
    assert parser._positionals._actions[2].choices.keys() == set(ALL_ACTIONS)


def test_no_action(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["conda-project"])
    with pytest.raises(SystemExit):
        assert main() is None

    out = capsys.readouterr().out
    assert "conda-project [-h] [-V] command" in out


def test_no_env_yaml(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr("sys.argv", ["conda-project", "install"])
    assert main() == 1

    err = capsys.readouterr().err
    assert "No conda environment.yml or environment.yaml file was found" in err


def test_unknown_action(capsys):
    with pytest.raises(SystemExit):
        assert parse_and_run(["__nope__"]) is None

    err = capsys.readouterr().err
    assert "invalid choice: '__nope__'" in err


@pytest.mark.parametrize("action", ALL_ACTIONS)
def test_cli_directory_argument(tmp_path, action, mocker, capsys):
    mocked_action = mocker.patch(
        f"conda_project.cli.commands.{action}",
        return_value=42,
        side_effect=print(f"I am {action}"),
    )

    ret = parse_and_run([action, "--directory", str(tmp_path)])
    assert ret == 42

    assert mocked_action.call_count == 1
    assert "directory" in mocked_action.call_args.args[0]

    out, err = capsys.readouterr()
    assert f"I am {action}\n" == out
    assert "" == err


@pytest.mark.parametrize("action", ENVIRONMENT_ACTIONS)
def test_environment_actions_verbose_true(action, mocker, project_directory_factory):
    if action == "init":
        method_to_patch = "create"
    elif action == "prepare":
        method_to_patch = "install"
    else:
        method_to_patch = action
    mocked_action = mocker.patch(f"conda_project.project.Environment.{method_to_patch}")

    if action == "create":
        project_path = project_directory_factory()
    else:
        env_yaml = "dependencies: []\n"
        project_path = project_directory_factory(env_yaml=env_yaml)

    ret = parse_and_run([action, "--directory", str(project_path)])
    assert ret == 0

    assert mocked_action.call_count == 1
    assert mocked_action.call_args.kwargs["verbose"]


@pytest.mark.parametrize("action", PROJECT_ACTIONS)
def test_project_actions_verbose_true(action, mocker, project_directory_factory):
    if action == "create":
        method_to_patch = "init"
    elif action == "prepare":
        method_to_patch = "install"
    else:
        method_to_patch = action

    mocked_action = mocker.patch(
        f"conda_project.project.CondaProject.{method_to_patch}"
    )
    if action in {"init", "create"}:
        project_path = project_directory_factory()
    else:
        env_yaml = "dependencies: []\n"
        project_path = project_directory_factory(env_yaml=env_yaml)

    ret = parse_and_run([action, "--directory", str(project_path)])
    assert ret == 0

    assert mocked_action.call_count == 1
    assert mocked_action.call_args.kwargs["verbose"]


def test_init_with_install(tmp_path, mocker):
    default_environment = mocker.spy(CondaProject, "default_environment")

    ret = parse_and_run(["init", "--directory", str(tmp_path), "--install"])
    assert ret == 0

    assert default_environment.install.call_count == 1


def test_init_from_environment(tmp_path, mocker: MockFixture):
    init = mocker.patch("conda_project.cli.commands.CondaProject.init")

    ret = parse_and_run(
        ["init", "--directory", str(tmp_path), "--from-environment", "base"]
    )
    assert ret == 0

    assert init.call_args.kwargs.get("from_environment") == "base"


@pytest.mark.parametrize("action", ENVIRONMENT_ACTIONS)
def test_action_with_environment_name(action, multi_env, mocker):
    environments = mocker.spy(CondaProject, "environments")
    default_environment = mocker.spy(CondaProject, "default_environment")

    ret = parse_and_run([action, "--directory", str(multi_env), "env1"])
    assert ret == 0

    if action == "prepare":
        method_to_spy = "install"
    else:
        method_to_spy = action

    assert getattr(default_environment, method_to_spy).call_count == 0

    assert environments.mock_calls[0] == mocker.call.__getitem__("env1")
    assert getattr(environments["env1"], method_to_spy).call_count == 1


@pytest.mark.parametrize("action", DEPENDENCIES_ACTIONS)
def test_deps_action_with_environment_name(action, multi_env, mocker):
    environments = mocker.spy(CondaProject, "environments")
    default_environment = mocker.spy(CondaProject, "default_environment")

    ret = parse_and_run(
        [action, "--directory", str(multi_env), "--environment", "env1", "pkg"]
    )
    assert ret == 0

    assert getattr(default_environment, action).call_count == 0

    assert environments.mock_calls[0] == mocker.call.__getitem__("env1")
    assert getattr(environments["env1"], action).call_count == 1


@pytest.mark.parametrize("action", ["install", "clean"])
def test_action_all_environments(action, mocker, multi_env):
    mocked_action = mocker.patch(f"conda_project.project.Environment.{action}")

    ret = parse_and_run([action, "--directory", str(multi_env), "--all"])
    assert ret == 0

    assert mocked_action.call_count == 2


def test_lock_all_environments(mocker, multi_env):
    mocked_lock = mocker.patch("conda_project.project.Environment.lock")

    ret = parse_and_run(["lock", "--directory", str(multi_env)])
    assert ret == 0

    assert mocked_lock.call_count == 2


def test_run_no_commands_fail(multi_env, capsys):
    return_code = parse_and_run(["run", "--directory", str(multi_env)])

    assert return_code == 1
    assert "no defined commands" in capsys.readouterr().err


def test_run_default_command(mocker, multi_env_multi_command):
    default_command = mocker.spy(CondaProject, "default_command")

    _ = parse_and_run(["run", "--directory", str(multi_env_multi_command)])

    assert default_command.run.call_args == mocker.call(
        environment=None, extra_args=[], external_environment=None, verbose=True
    )


def test_run_default_command_with_env(mocker, multi_env_multi_command):
    default_command = mocker.spy(CondaProject, "default_command")

    _ = parse_and_run(
        ["run", "--directory", str(multi_env_multi_command), "--environment", "env2"]
    )

    assert default_command.run.call_args == mocker.call(
        environment="env2", extra_args=[], external_environment=None, verbose=True
    )


def test_run_named_command(mocker, multi_env_multi_command):
    default_command = mocker.spy(CondaProject, "default_command")
    commands = mocker.spy(CondaProject, "commands")

    _ = parse_and_run(["run", "--directory", str(multi_env_multi_command), "cmd1"])

    assert default_command.run.call_count == 0

    assert commands.mock_calls[0] == mocker.call.__getitem__("cmd1")
    assert commands["cmd1"].run.call_count == 1


def test_run_unnamed_command(mocker, multi_env_multi_command):
    from conda_project.cli import commands as commands_module

    command = mocker.spy(commands_module, "Command")
    project = mocker.spy(commands_module, "CondaProject")

    mocked_run = mocker.patch("conda_project.project.Command.run")

    _ = parse_and_run(["run", "--directory", str(multi_env_multi_command), "cmd3"])

    assert command.call_args == mocker.call(
        name="cmd3",
        cmd="cmd3",
        environment=project.spy_return.default_environment,
        project=project.spy_return,
    )
    assert mocked_run.call_args == mocker.call(
        environment=None, extra_args=[], external_environment=None, verbose=True
    )


def test_run_unnamed_command_with_env(mocker, multi_env_multi_command):
    from conda_project.cli import commands as commands_module

    command = mocker.spy(commands_module, "Command")
    project = mocker.spy(commands_module, "CondaProject")

    mocked_run = mocker.patch("conda_project.project.Command.run")

    _ = parse_and_run(
        [
            "run",
            "--directory",
            str(multi_env_multi_command),
            "--environment",
            "env2",
            "cmd3",
        ]
    )

    assert command.call_args == mocker.call(
        name="cmd3",
        cmd="cmd3",
        environment=project.spy_return.default_environment,
        project=project.spy_return,
    )
    assert mocked_run.call_args == mocker.call(
        environment="env2", extra_args=[], external_environment=None, verbose=True
    )


def test_run_unnamed_command_with_extra_args(mocker, multi_env_multi_command):
    from conda_project.cli import commands as commands_module

    command = mocker.spy(commands_module, "Command")
    project = mocker.spy(commands_module, "CondaProject")

    mocked_run = mocker.patch("conda_project.project.Command.run")

    _ = parse_and_run(
        [
            "run",
            "--directory",
            str(multi_env_multi_command),
            "--environment",
            "env2",
            "cmd3",
            "--flag",
            "value",
            "arg1",
        ]
    )

    assert command.call_args == mocker.call(
        name="cmd3",
        cmd="cmd3",
        environment=project.spy_return.default_environment,
        project=project.spy_return,
    )
    assert mocked_run.call_args == mocker.call(
        environment="env2",
        extra_args=["--flag", "value", "arg1"],
        external_environment=None,
        verbose=True,
    )


@pytest.mark.parametrize("action", ("lock", "check", "install", "activate", "run"))
def test_cli_archive_arguments(tmp_path, action, mocker, capsys):
    mocked_action = mocker.patch(
        f"conda_project.cli.commands.{action}",
        return_value=42,
        side_effect=print(f"I am {action}"),
    )

    ret = parse_and_run(
        [action, "--project-archive", "project.tar.gz", "--directory", str(tmp_path)]
    )
    assert ret == 42

    assert mocked_action.call_count == 1
    assert "project_archive" in mocked_action.call_args.args[0]
    assert "archive_storage_options" in mocked_action.call_args.args[0]

    out, err = capsys.readouterr()
    assert f"I am {action}\n" == out
    assert "" == err


def test_archive_storage_options_remote(mocker):
    mocked_project = mocker.patch("conda_project.cli.commands.CondaProject")

    args = Namespace(
        project_archive="protocol://bucket/file.zip",
        archive_storage_options="key1=valueA,key2=valueB",
        directory=None,
    )

    _ = _load_project(args)

    assert mocked_project.from_archive.call_args.kwargs["storage_options"] == {
        "key1": "valueA",
        "key2": "valueB",
    }


@pytest.mark.slow()
@pytest.mark.parametrize(
    "for_command,expected_env", [(None, "bbb"), ("default", "default")]
)
def test_install_env_for_command(project_directory_factory, for_command, expected_env):

    env_yaml = f"dependencies: []\nplatforms: [{current_platform()}]"

    project_yaml = dedent(
        f"""\
        name: test
        environments:
          bbb: [env1{project_directory_factory._suffix}]
          default: [env2{project_directory_factory._suffix}]
        commands:
          default:
            cmd: true
            environment: default
        """
    )

    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"env1{project_directory_factory._suffix}": env_yaml,
            f"env2{project_directory_factory._suffix}": env_yaml,
        },
    )

    with pytest.raises(CondaProjectError):
        args = Namespace(
            directory=project_path,
            environment="env",
            project_archive=None,
            archive_storage_options=None,
            for_command="cmd",
        )
        project = _load_project(args)

        _ = _get_environment_from_args(project, args)

    args = Namespace(
        directory=project_path,
        environment=None,
        project_archive=None,
        archive_storage_options=None,
        for_command=for_command,
    )
    project = _load_project(args)

    env = _get_environment_from_args(project, args)
    assert env.name == expected_env
