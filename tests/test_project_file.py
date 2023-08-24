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
    UniqueOrderedList,
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


def test_uniqueordreredlist_init():
    inputs = ["a", "c", "b", "c"]

    uol = UniqueOrderedList(inputs)
    assert uol == ["a", "c", "b"]


def test_uniqueorderedlist_append_extend():
    inputs = ["a", "c", "b", "c"]
    uol = UniqueOrderedList(inputs)

    uol.append("c")
    assert uol == ["a", "c", "b"]

    addition = ["b", "e", "d", "a"]
    uol.extend(addition)
    assert uol == ["a", "c", "b", "e", "d"]


def test_env_add_dependencies():
    env = EnvironmentYaml(dependencies=["python=3.10", "numpy"])

    env.add_dependencies(["pandas", "dask"])
    assert env.dependencies == ["python=3.10", "numpy", "pandas", "dask"]


def test_env_add_pip_dependencies():
    env = EnvironmentYaml(dependencies=["python=3.10", "pip"])

    env.add_dependencies(["pypi::requests"])
    assert env.dependencies == ["python=3.10", "pip", {"pip": ["requests"]}]


def test_env_add_dependencies_empty_channels():
    env = EnvironmentYaml(dependencies=["python=3.10", "numpy"])

    assert env.channels is None

    env.add_dependencies(["hvplot", "geoviews"], channels=["conda-forge", "defaults"])
    assert env.dependencies == ["python=3.10", "numpy", "hvplot", "geoviews"]
    assert env.channels == ["conda-forge", "defaults"]


def test_env_add_dependencies_with_channels():
    env = EnvironmentYaml(dependencies=["python=3.10", "numpy"], channels=["defaults"])

    assert isinstance(env.channels, UniqueOrderedList)

    env.add_dependencies(["pandas", "dask"], channels=["conda-forge", "defaults"])

    assert env.dependencies == ["python=3.10", "numpy", "pandas", "dask"]
    assert env.channels == ["defaults", "conda-forge"]


def test_replace_dependency():
    env = EnvironmentYaml(
        dependencies=["python=3.10", "numpy", "conda-forge::pandas", "requests<2.31"],
        channels=["defaults"],
    )

    env.add_dependencies(["pandas<2", "requests"])

    assert env.dependencies == ["python=3.10", "numpy", "pandas<2", "requests"]


def test_env_comparison():
    env = EnvironmentYaml(dependencies=["python=3.10"])

    env_with_channels = EnvironmentYaml(
        dependencies=["python=3.10"], channels=["defaults"]
    )

    assert env != env_with_channels


def test_remove_dependencies():
    env = EnvironmentYaml(
        dependencies=["python=3.10", "numpy", "conda-forge::pandas>=2"],
        channels=["defaults"],
    )

    env.remove_dependencies(["numpy", "pandas"])

    assert env.dependencies == ["python=3.10"]


def test_remove_dependencies_extra_fields():
    env = EnvironmentYaml(
        dependencies=["python=3.10", "numpy", "conda-forge::pandas>=2"],
        channels=["defaults"],
    )

    env.remove_dependencies(["conda-forge::numpy", "pandas[stuff]"])

    assert env.dependencies == ["python=3.10"]


def test_env_add_pip_dependencies_no_pip(capsys):
    env = EnvironmentYaml(dependencies=["python=3.10"])

    env.add_dependencies(["pypi::requests"])
    assert env.dependencies == ["python=3.10", "pip", {"pip": ["requests"]}]
    assert "do not list pip itself" in capsys.readouterr().out


def test_env_replace_pip_dependency():
    env = EnvironmentYaml(
        dependencies=["python=3.10", "pip", {"pip": ["pydantic[dotenv]"]}]
    )

    env.add_dependencies(["pypi::pydantic[dotenv,email]<2"])
    assert env.dependencies == [
        "python=3.10",
        "pip",
        {"pip": ["pydantic[dotenv,email]<2"]},
    ]


def test_remove_pip_dependency():
    env = EnvironmentYaml(
        dependencies=["python=3.10", "pip", {"pip": ["pydantic[dotenv]"]}]
    )

    env.remove_dependencies(["pypi::pydantic"])
    assert env.dependencies == ["python=3.10", "pip", {"pip": []}]


def test_remove_pip_dependency_extras():
    env = EnvironmentYaml(
        dependencies=["python=3.10", "pip", {"pip": ["pydantic[dotenv]"]}]
    )

    env.remove_dependencies(["pypi::pydantic<2"])
    assert env.dependencies == ["python=3.10", "pip", {"pip": []}]
