# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import os
import pytest

from conda_project.utils import env_variable, find_file
from conda_project.exceptions import CondaProjectError


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
