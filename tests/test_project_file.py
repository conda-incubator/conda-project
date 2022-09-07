# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from io import StringIO
from pathlib import Path
from textwrap import dedent
from typing import Dict, List, Optional, Union

import pytest

from conda_project.exceptions import CondaProjectError
from conda_project.project_file import BaseYaml, CondaProjectYaml, EnvironmentYaml


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
    yml.yaml(stream)
    assert stream.getvalue() == "filled: foo\nnested:\n  a:\n    - b\n  d: []\n"


def test_bad_yaml_file():
    class YamlFile(BaseYaml):
        attribute: str

    yml = "attribute: correct\nmore_attributes: wrong"

    with pytest.raises(CondaProjectError) as exinfo:
        _ = YamlFile.parse_yaml(yml)

    assert "validation error for YamlFile" in str(exinfo.value)


def test_miss_spelled_env_yaml_file():
    environment_yaml = dedent(
        """\
        name: misspelled
        channel:
            - defaults

        dependencies: []
        """
    )

    with pytest.raises(CondaProjectError) as exinfo:
        _ = EnvironmentYaml.parse_yaml(environment_yaml)

    assert "validation error for EnvironmentYaml" in str(exinfo.value)


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
        """
    )

    assert written_contents == expected_contents
