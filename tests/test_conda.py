# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os

import pytest

from conda_project.conda import call_conda, conda_info, conda_run, current_platform
from conda_project.exceptions import CondaProjectError


def test_local_condarc(tmp_path):
    condarc = "channels: [__conda-project-test]\n"
    condarc_file = tmp_path / ".condarc"
    with condarc_file.open("wt") as f:
        f.write(condarc)

    proc = call_conda(
        ["config", "--show", "channels"],
        condarc_path=condarc_file,
        verbose=False,
    )
    channels = proc.stdout.splitlines()
    assert channels[1] == "  - __conda-project-test"


def test_conda_error():
    with pytest.raises(CondaProjectError) as excinfo:
        _ = call_conda(["not-a-command"], verbose=False)

    assert "Failed to run" in str(excinfo.value)


def test_conda_output():
    proc = call_conda(["info"], verbose=False)
    assert "active environment" in proc.stdout

    proc = call_conda(["info"], verbose=True)
    assert not proc.stdout


def test_conda_info():
    info = conda_info()
    assert "platform" in info
    assert "conda_version" in info


@pytest.fixture()
def disable_current_platform_cache():
    """Ensure current_platform cache is cleared before and after test."""
    current_platform.cache_clear()
    yield
    current_platform.cache_clear()


@pytest.mark.usefixtures("disable_current_platform_cache")
def test_current_platform(monkeypatch):
    monkeypatch.setenv("CONDA_SUBDIR", "monkey-64")
    platform = current_platform()
    assert platform == "monkey-64"


def test_conda_run_without_env(execvpe, empty_conda_environment):
    conda_run(
        cmd="dummy-cmd",
        prefix=empty_conda_environment,
        working_dir=empty_conda_environment,
        env=None,
    )

    assert execvpe["env"] == {}


def test_conda_run_with_variables(execvpe, empty_conda_environment):
    variables = {"FOO": "bar"}
    conda_run(
        cmd="dummy-cmd",
        prefix=empty_conda_environment,
        working_dir=empty_conda_environment,
        env=variables,
    )

    assert execvpe["env"] == variables


def test_conda_run_working_dir(execvpe, empty_conda_environment):
    current_dir = os.getcwd()
    conda_run(
        cmd="dummy-cmd",
        prefix=empty_conda_environment,
        working_dir=empty_conda_environment,
        env=None,
    )

    assert execvpe["cwd"] == str(empty_conda_environment)
    assert os.getcwd() == current_dir


def test_conda_run_failed_working_dir(execvpe_failed, empty_conda_environment):
    current_dir = os.getcwd()
    with pytest.raises(RuntimeError):
        conda_run(
            cmd="dummy-cmd",
            prefix=empty_conda_environment,
            working_dir=empty_conda_environment,
            env=None,
        )

    assert execvpe_failed["cwd"] == str(empty_conda_environment)
    assert os.getcwd() == current_dir
