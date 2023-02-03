# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from functools import partial
from textwrap import dedent

import pytest

from conda_project.cli.main import cli, main, parse_and_run

PROJECT_COMMANDS = ("create", "check")
ENVIRONMENT_COMMANDS = ("clean", "prepare", "lock")
ALL_COMMANDS = PROJECT_COMMANDS + ENVIRONMENT_COMMANDS


def test_known_commands():
    parser = cli()
    assert parser._positionals._actions[2].choices.keys() == set(ALL_COMMANDS)


def test_no_command(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["conda-project"])
    with pytest.raises(SystemExit):
        assert main() is None

    out = capsys.readouterr().out
    assert "conda-project [-h] [-V] command" in out


def test_no_env_yaml(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr("sys.argv", ["conda-project", "prepare"])
    assert main() == 1

    err = capsys.readouterr().err
    assert "No conda environment.yml or environment.yaml file was found" in err


def test_unknown_command(capsys):
    with pytest.raises(SystemExit):
        assert parse_and_run(["__nope__"]) is None

    err = capsys.readouterr().err
    assert "invalid choice: '__nope__'" in err


@pytest.mark.parametrize("command", ALL_COMMANDS)
def test_command_args(command, monkeypatch, capsys):
    def mocked_command(command, args):
        print(f"I am {command}")
        assert args.directory == "project-dir"
        return 42

    monkeypatch.setattr(
        f"conda_project.cli.commands.{command}", partial(mocked_command, command)
    )

    ret = parse_and_run([command, "--directory", "project-dir"])
    assert ret == 42

    out, err = capsys.readouterr()
    assert f"I am {command}\n" == out
    assert "" == err


@pytest.mark.parametrize("command", ENVIRONMENT_COMMANDS)
@pytest.mark.parametrize("project_directory_factory", [".yml", ".yaml"], indirect=True)
def test_cli_verbose_env(command, monkeypatch, project_directory_factory):
    if command == "create":
        project_path = project_directory_factory()
    else:
        env_yaml = "dependencies: []\n"
        project_path = project_directory_factory(env_yaml=env_yaml)

    def mocked_action(*_, **kwargs):
        assert kwargs.get("verbose", False)

    monkeypatch.setattr(f"conda_project.project.Environment.{command}", mocked_action)

    ret = parse_and_run([command, "--directory", str(project_path)])
    assert ret == 0


@pytest.mark.parametrize("command", PROJECT_COMMANDS)
def test_cli_verbose_project(command, monkeypatch, project_directory_factory):
    if command == "create":
        project_path = project_directory_factory()
    else:
        env_yaml = "dependencies: []\n"
        project_path = project_directory_factory(env_yaml=env_yaml)

    def mocked_action(*_, **kwargs):
        assert kwargs.get("verbose", False)

    monkeypatch.setattr(f"conda_project.project.CondaProject.{command}", mocked_action)

    _ = parse_and_run([command, "--directory", str(project_path)])


def test_create_with_prepare(tmp_path):
    ret = parse_and_run(["create", "--directory", str(tmp_path), "--prepare"])

    assert ret == 0

    assert (tmp_path / "envs" / "default" / "conda-meta" / "history").exists()


@pytest.mark.parametrize("command", ENVIRONMENT_COMMANDS)
def test_command_with_environment_name(command, monkeypatch, project_directory_factory):
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

    def mocked_action(self, *args, **kwargs):
        assert self.name == "env1"

    monkeypatch.setattr(f"conda_project.project.Environment.{command}", mocked_action)

    ret = parse_and_run([command, "--directory", str(project_path), "env1"])
    assert ret == 0


def test_prepare_and_clean_all_environments(monkeypatch, project_directory_factory):
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

    def mocked_action(self, *args, **kwargs):
        assert self.name in ["env1", "env2"]

    monkeypatch.setattr("conda_project.project.Environment.prepare", mocked_action)
    monkeypatch.setattr("conda_project.project.Environment.clean", mocked_action)

    ret = parse_and_run(["prepare", "--directory", str(project_path), "--all"])
    assert ret == 0

    ret = parse_and_run(["clean", "--directory", str(project_path), "--all"])
    assert ret == 0


def test_lock_all_environments(monkeypatch, project_directory_factory):
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

    def mocked_action(self, *args, **kwargs):
        assert self.name in ["env1", "env2"]

    monkeypatch.setattr("conda_project.project.Environment.lock", mocked_action)

    ret = parse_and_run(["lock", "--directory", str(project_path)])
    assert ret == 0


@pytest.mark.slow
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

    ret = parse_and_run(["check", "--directory", str(project_path)])
    assert ret == 1

    stderr = capsys.readouterr().err
    assert "The environment env1 is not locked" in stderr
    assert "The environment env2 is not locked" in stderr

    ret = parse_and_run(["lock", "--directory", str(project_path)])
    assert ret == 0

    ret = parse_and_run(["check", "--directory", str(project_path)])
    assert ret == 0

    env1 = "dependencies: [python=3.8]\n"
    with (project_path / f"env1{project_directory_factory._suffix}").open("w") as f:
        f.write(env1)

    ret = parse_and_run(["check", "--directory", str(project_path)])
    assert ret == 1

    stderr = capsys.readouterr().err
    assert stderr
    assert "The lockfile for environment env1 is out-of-date" in stderr
    assert "The lockfile for environment env2" not in stderr

    env2 = "dependencies: [python=3.8]\n"
    with (project_path / f"env2{project_directory_factory._suffix}").open("w") as f:
        f.write(env2)

    ret = parse_and_run(["check", "--directory", str(project_path)])
    assert ret == 1

    stderr = capsys.readouterr().err
    assert stderr
    assert "The lockfile for environment env1 is out-of-date" in stderr
    assert "The lockfile for environment env2 is out-of-date" in stderr
