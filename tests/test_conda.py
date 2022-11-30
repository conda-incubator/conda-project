# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda_project.conda import call_conda, conda_info, current_platform
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


def test_current_platform(monkeypatch):
    monkeypatch.setenv("CONDA_SUBDIR", "monkey-64")
    current_platform.cache_clear()
    platform = current_platform()
    assert platform == "monkey-64"
