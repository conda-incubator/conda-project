# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
from functools import partial

import pytest

from conda_project.cli.main import cli, main, parse_and_run

COMMANDS = ["create", "clean", "prepare", "lock"]


def test_known_commands():
    parser = cli()
    assert parser._positionals._actions[2].choices.keys() == set(COMMANDS)


def test_no_command(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["conda-project"])
    with pytest.raises(SystemExit):
        assert main() is None

    out = capsys.readouterr().out
    assert "conda-project [-h] [-V] command" in out


def test_no_env_yaml(tmpdir, monkeypatch, capsys):
    monkeypatch.chdir(tmpdir)

    monkeypatch.setattr("sys.argv", ["conda-project", "prepare"])
    assert main() == 1

    err = capsys.readouterr().err
    assert "No Conda environment.yml or environment.yaml file was found" in err


def test_unknown_command(capsys):
    with pytest.raises(SystemExit):
        assert parse_and_run(["nope"]) is None

    err = capsys.readouterr().err
    assert "invalid choice: 'nope'" in err


@pytest.mark.parametrize("command", COMMANDS)
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


@pytest.mark.parametrize("command", COMMANDS)
def test_cli_verbose(command, monkeypatch, project_directory_factory):
    if command == "create":
        project_path = project_directory_factory()
    else:
        env_yaml = "dependencies: []\n"
        project_path = project_directory_factory(env_yaml=env_yaml)

    def mocked_action(*args, **kwargs):
        assert kwargs.get("verbose", False)

    monkeypatch.setattr(f"conda_project.project.CondaProject.{command}", mocked_action)

    ret = parse_and_run([command, "--directory", str(project_path)])
    assert ret == 0


def test_create_with_prepare(tmpdir):
    ret = parse_and_run(["create", "--directory", str(tmpdir), "--prepare"])

    assert ret == 0

    assert os.path.exists(
        os.path.join(tmpdir, "envs", "default", "conda-meta", "history")
    )


@pytest.mark.parametrize("command", ["lock", "prepare", "clean"])
def test_command_with_environment_name(command, monkeypatch, project_directory_factory):
    env1 = env2 = "dependencies: []\n"
    project_yaml = f"""name: multi-envs
environments:
  env1: [env1{project_directory_factory._suffix}]
  env2: [env2{project_directory_factory._suffix}]
"""
    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"env1{project_directory_factory._suffix}": env1,
            f"env2{project_directory_factory._suffix}": env2,
        },
    )

    def mocked_action(*args, **kwargs):
        assert kwargs.get("environment", False) == "env1"

    monkeypatch.setattr(f"conda_project.project.CondaProject.{command}", mocked_action)

    ret = parse_and_run([command, "--directory", str(project_path), "env1"])
    assert ret == 0


@pytest.mark.parametrize("command", ["lock", "prepare", "clean"])
def test_command_all_environments(command, monkeypatch, project_directory_factory):
    env1 = env2 = "dependencies: []\n"
    project_yaml = f"""name: multi-envs
environments:
  env1: [env1{project_directory_factory._suffix}]
  env2: [env2{project_directory_factory._suffix}]
"""
    project_path = project_directory_factory(
        project_yaml=project_yaml,
        files={
            f"env1{project_directory_factory._suffix}": env1,
            f"env2{project_directory_factory._suffix}": env2,
        },
    )

    def mocked_action(*args, **kwargs):
        assert kwargs.get("environment", False).name in ["env1", "env2"]

    monkeypatch.setattr(f"conda_project.project.CondaProject.{command}", mocked_action)

    ret = parse_and_run([command, "--directory", str(project_path), "--all"])
    assert ret == 0
