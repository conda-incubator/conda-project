# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import os

import pytest

from conda_project.exceptions import CondaProjectError
from conda_project.utils import env_variable, find_file, prepare_variables


def test_env_var_context():
    foo = "_conda_project_foo"
    assert foo not in os.environ

    with env_variable(foo, "bar"):
        assert os.getenv(foo) == "bar"

    assert foo not in os.environ


def test_replace_env_var_context():
    foo = "_conda_project_foo"
    os.environ[foo] = "bar"

    with env_variable(foo, "baz"):
        assert os.getenv(foo) == "baz"

    assert os.getenv(foo) == "bar"


def test_find_file(tmp_path):
    yaml = tmp_path / "file.yaml"
    yml = tmp_path / "file.yml"

    yaml.touch()
    yml.touch()

    assert find_file(tmp_path, ("missing.yml",)) is None
    assert find_file(tmp_path, ("file.yml",)) == yml.resolve()
    assert find_file(tmp_path, ("file.yaml",)) == yaml.resolve()

    with pytest.raises(CondaProjectError):
        find_file(tmp_path, ("file.yaml", "file.yml"))


def test_prepare_variables_from_environ(tmp_path):
    env = prepare_variables(tmp_path)

    assert env == os.environ


def test_prepare_variables_from_project(tmp_path):
    variables = {"FOO": "set-by-project"}

    env = prepare_variables(tmp_path, variables)

    assert env.get("FOO") == "set-by-project"


def test_prepare_variables_from_dotenv(tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text("FOO=from-dot-env")

    env = prepare_variables(tmp_path)

    assert env.get("FOO") == "from-dot-env"


def test_prepare_variables_override_environ(tmp_path, monkeypatch):
    variables = {"FOO": "set-by-project"}
    monkeypatch.setenv("FOO", "set-by-environ")

    env = prepare_variables(tmp_path, variables)

    assert env.get("FOO") == "set-by-environ"


def test_prepare_variables_override_dotenv(tmp_path):
    variables = {"FOO": "set-by-project"}
    dotenv = tmp_path / ".env"
    dotenv.write_text("FOO=from-dot-env")

    env = prepare_variables(tmp_path, variables)

    assert env.get("FOO") == "from-dot-env"


def test_prepare_variables_override_environ_and_dotenv(tmp_path, monkeypatch):
    monkeypatch.setenv("FOO", "set-by-environ")
    variables = {"FOO": "set-by-project"}
    dotenv = tmp_path / ".env"
    dotenv.write_text("FOO=from-dot-env")

    env = prepare_variables(tmp_path, variables)

    assert env.get("FOO") == "set-by-environ"


def test_prepare_variables_none_override_environ(tmp_path, monkeypatch):
    variables = {"FOO": None}
    monkeypatch.setenv("FOO", "set-by-environ")

    env = prepare_variables(tmp_path, variables)

    assert env.get("FOO") == "set-by-environ"


def test_prepare_variables_none_override_dotenv(tmp_path):
    variables = {"FOO": None}
    dotenv = tmp_path / ".env"
    dotenv.write_text("FOO=from-dot-env")

    env = prepare_variables(tmp_path, variables)

    assert env.get("FOO") == "from-dot-env"


def test_prepare_variables_none_override_environ_and_dotenv(tmp_path, monkeypatch):
    monkeypatch.setenv("FOO", "set-by-environ")
    variables = {"FOO": None}
    dotenv = tmp_path / ".env"
    dotenv.write_text("FOO=from-dot-env")

    env = prepare_variables(tmp_path, variables)

    assert env.get("FOO") == "set-by-environ"


def test_prepare_variables_fail(tmp_path):
    variables = {"FOO": None}

    with pytest.raises(CondaProjectError) as e:
        prepare_variables(tmp_path, variables)

        assert "do not have a default value" in str(e)


def test_variable_overrides_by_command(tmp_path):
    project_variables = {"FOO": None}
    command_variables = {"FOO": "set-by-command"}

    env = prepare_variables(tmp_path, project_variables, command_variables)

    assert env.get("FOO") == "set-by-command"


def test_variable_overrides_by_command_and_dotenv(tmp_path):
    project_variables = {"FOO": None}
    command_variables = {"FOO": "set-by-command"}
    dotenv = tmp_path / ".env"
    dotenv.write_text("FOO=from-dot-env")

    env = prepare_variables(tmp_path, project_variables, command_variables)

    assert env.get("FOO") == "from-dot-env"


def test_variable_overrides_by_command_and_dotenv_and_environ(tmp_path, monkeypatch):
    project_variables = {"FOO": None}
    command_variables = {"FOO": "set-by-command"}
    dotenv = tmp_path / ".env"
    dotenv.write_text("FOO=from-dot-env")
    monkeypatch.setenv("FOO", "set-by-environ")

    env = prepare_variables(tmp_path, project_variables, command_variables)

    assert env.get("FOO") == "set-by-environ"


def test_prepare_variables_override_fail(tmp_path):
    project_variables = {"FOO": "bar"}
    command_variables = {"FOO": None}

    with pytest.raises(CondaProjectError) as e:
        prepare_variables(tmp_path, project_variables, command_variables)

        assert "do not have a default value" in str(e)


def test_variables_is_none_or_empty(tmp_path):
    env = prepare_variables(tmp_path, None, None)
    assert env == os.environ

    env = prepare_variables(tmp_path, {}, {})
    assert env == os.environ
