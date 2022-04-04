# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest
from functools import partial

from conda_project.cli.main import main, parse_and_run

COMMANDS = ['prepare', 'clean']


def test_no_command(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["conda-project"])
    with pytest.raises(SystemExit):
        assert main() is None

    out = capsys.readouterr().out
    assert 'conda-project [-h] [-V] command' in out


def test_no_env_yaml(tmpdir, monkeypatch, capsys):
    monkeypatch.chdir(tmpdir)

    monkeypatch.setattr("sys.argv", ["conda-project", "prepare"])
    assert main() == 1

    err = capsys.readouterr().err
    assert 'No Conda environment.yml or environment.yaml file was found' in err


def test_unknown_command(capsys):
    with pytest.raises(SystemExit):
        assert parse_and_run(['nope']) is None

    err = capsys.readouterr().err
    assert "invalid choice: 'nope'" in err


@pytest.mark.parametrize('command', COMMANDS)
def test_command_args(command, monkeypatch, capsys):
    def mocked_command(command, args):
        print(f'I am {command}')
        assert args.directory == 'project-dir'
        return 42

    monkeypatch.setattr(f'conda_project.cli.commands.{command}',
                        partial(mocked_command, command))

    ret = parse_and_run([command, '--directory', 'project-dir'])
    assert ret == 42

    out, err = capsys.readouterr()
    assert f"I am {command}\n" == out
    assert "" == err


@pytest.mark.parametrize('command', COMMANDS)
def test_cli_verbose(command, monkeypatch):
    def mocked_action(*args, **kwargs):
        assert kwargs.get('verbose', False)

    monkeypatch.setattr(f'conda_project.project.CondaProject.{command}', mocked_action)

    ret = parse_and_run([command])
    assert ret == 0
