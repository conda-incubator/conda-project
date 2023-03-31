# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from io import StringIO
from pathlib import Path
from textwrap import dedent
from typing import Dict, List, Optional, Union

import pytest
from pydantic import ValidationError

from conda_project.exceptions import CondaProjectError
from conda_project.project_file import (
    BaseYaml,
    Command,
    CondaProjectYaml,
    EnvironmentYaml,
)


def test_empty_environment():
    env_dict = {"dependencies": []}

    env = EnvironmentYaml(**env_dict)
    assert env.name is None
    assert env.dependencies == []
    assert env.channels is None
    assert env.variables is None
    assert env.prefix is None


def test_unsupported_key_in_dependencies():
    env_dict = {"name": "unsupported", "dependencies": ["python", {"npm": ["foo"]}]}

    with pytest.raises(ValueError):
        _ = EnvironmentYaml(**env_dict)


def test_yaml_parse_error():
    class Yaml(BaseYaml):
        foo: int

    yml = dedent(
        """\
        foo: a
        """
    )

    with pytest.raises(CondaProjectError):
        _ = Yaml.parse_yaml(yml)


def test_to_yaml_with_indent():
    class Yaml(BaseYaml):
        foo: str
        stuff: List[str]

    yml = Yaml(foo="bar", stuff=["thing1", "thing2"])
    stream = StringIO()
    yml.yaml(stream)
    assert stream.getvalue() == "foo: bar\nstuff:\n  - thing1\n  - thing2\n"


def test_yaml_dump_skip_empty_keys():
    class Yaml(BaseYaml):
        filled: str
        empty: Optional[str] = None
        nested: Dict[str, Union[None, List[str]]] = {}

    yml = Yaml(filled="foo", nested={"a": ["b"], "c": None, "d": []})
    stream = StringIO()
    yml.yaml(stream, drop_empty_keys=True)
    assert stream.getvalue() == "filled: foo\nnested:\n  a:\n    - b\n  d: []\n"


def test_yaml_anchors():
    class YamlFile(BaseYaml):
        a: str
        b: str

    yml = dedent(
        """\
        a: &a foo
        b: *a
        """
    )

    yml = YamlFile.parse_yaml(yml)
    assert yml.a == "foo"
    assert yml.b == "foo"


def test_yaml_anchors_extra():
    class YamlFile(BaseYaml):
        a: str
        b: str

    yml = dedent(
        """\
        _hidden: &a foo
        a: *a
        b: *a
        """
    )

    yml = YamlFile.parse_yaml(yml)
    assert yml.a == "foo"
    assert yml.b == "foo"


def test_empty_project_yaml_file():
    environment_yaml = ""

    with pytest.raises(CondaProjectError) as exinfo:
        _ = CondaProjectYaml.parse_yaml(environment_yaml)

    assert "The file appears to be empty." in str(exinfo.value)


def test_project_file_with_one_env():
    project_dict = {
        "name": "one-env",
        "environments": {"default": ["./environment.yml"]},
    }

    project_file = CondaProjectYaml(**project_dict)
    assert project_file.name == "one-env"
    assert project_file.environments["default"] == [Path("./environment.yml")]


def test_project_yaml_round_trip():
    project_file_input = dedent(
        """\
        name: my-project
        # comment
        environments:
          default:
            - ./environment.yml
            - ../dev.yaml
          another:
            - another-env.yml
        """
    )

    project_file = CondaProjectYaml.parse_yaml(project_file_input)

    stream = StringIO()
    project_file.yaml(stream)

    written_contents = stream.getvalue()

    expected_contents = dedent(
        """\
        name: my-project
        environments:
          default:
            - environment.yml
            - ../dev.yaml
          another:
            - another-env.yml
        variables: {}
        commands: {}
        """
    )

    assert written_contents == expected_contents


def test_command_without_env():
    command = {"cmd": "run-this"}

    parsed = Command(**command)
    assert parsed.environment is None


def test_command_with_env_name():
    command = {"cmd": "run-this", "environment": "default"}

    parsed = Command(**command)
    assert parsed.environment == "default"


def test_command_fails_with_env_non_string():
    command = {"cmd": "run-this", "environment": type}

    with pytest.raises(ValidationError):
        _ = Command(**command)


def test_command_failed_with_extra_keys():
    command = {"cmd": "run-this", "extra": "nope"}

    with pytest.raises(ValidationError):
        _ = Command(**command)


def test_command_without_variables():
    command = {"cmd": "run-this"}

    parsed = Command(**command)
    assert parsed.variables is None


def test_command_with_variable():
    command = {"cmd": "run-this", "variables": {"FOO": "bar"}}

    parsed = Command(**command)
    assert parsed.variables is not None
    assert parsed.variables.get("FOO") == "bar"


def test_command_with_empty_variable():
    command = {"cmd": "run-this", "variables": {"FOO": None}}

    parsed = Command(**command)
    assert parsed.variables is not None
    assert parsed.variables.get("FOO") is None
