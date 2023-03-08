# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import pytest

from conda_project.conda import (
    call_conda,
    conda_activate,
    conda_info,
    conda_run,
    current_platform,
    is_windows,
)
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


def test_conda_run_without_variables(mocked_execvped, empty_conda_environment):
    conda_run(
        cmd="dummy-cmd",
        prefix=empty_conda_environment,
        working_dir=empty_conda_environment,
        env=None,
    )

    assert mocked_execvped.call_count == 1
    assert mocked_execvped.call_args.kwargs["env"] == {}

    if not is_windows():
        assert mocked_execvped.call_args.kwargs["args"][0] == "-c"
    else:
        assert mocked_execvped.call_args.kwargs["args"][0] == "/d"


def test_conda_run_with_variables(mocked_execvped, empty_conda_environment):
    variables = {"FOO": "bar"}
    conda_run(
        cmd="dummy-cmd",
        prefix=empty_conda_environment,
        working_dir=empty_conda_environment,
        env=variables,
    )

    assert mocked_execvped.call_count == 1
    assert mocked_execvped.call_args.kwargs["env"] == variables
    if not is_windows():
        assert mocked_execvped.call_args.kwargs["args"][0] == "-c"
    else:
        assert mocked_execvped.call_args.kwargs["args"][0] == "/d"


def test_conda_run_extra_args(mocker, mocked_execvped, empty_conda_environment):
    import conda_project.conda

    wrap_subprocess_call = mocker.spy(conda_project.conda, "wrap_subprocess_call")

    extra_args = ["arg", "-f", "--flag", "import os; print(os.environ['FOO' ])"]
    conda_run(
        cmd="dummy-cmd",
        extra_args=extra_args,
        prefix=empty_conda_environment,
        working_dir=empty_conda_environment,
        env=None,
    )

    assert wrap_subprocess_call.call_count == 1
    assert wrap_subprocess_call.call_args.kwargs["arguments"] == [
        "dummy-cmd",
        *extra_args,
    ]
    assert mocked_execvped.call_count == 1


@pytest.mark.skipif(is_windows(), reason="On Windows we call subprocess")
def test_conda_activate_pexpect(mocker, empty_conda_environment, capsys):
    mocked_spawn = mocker.patch("conda_project.conda.pexpect.spawn")
    mocker.patch(
        "conda_project.conda.shellingham.detect_shell",
        return_value=("/bin/sh", "/bin/sh"),
    )
    mocker.patch("conda_project.conda._send_activation")

    conda_activate(
        prefix=empty_conda_environment, working_dir=empty_conda_environment, env=None
    )

    assert "activated in a new shell" in capsys.readouterr().out

    assert mocked_spawn.call_args == mocker.call(
        command="/bin/sh", args=["-i"], cwd=empty_conda_environment, env={}, echo=False
    )


@pytest.mark.skipif(is_windows(), reason="On Windows we call subprocess")
def test_conda_activate_pexpect_with_variables(mocker, empty_conda_environment, capsys):
    mocked_spawn = mocker.patch("conda_project.conda.pexpect.spawn")
    mocker.patch(
        "conda_project.conda.shellingham.detect_shell",
        return_value=("/bin/sh", "/bin/sh"),
    )
    mocker.patch("conda_project.conda._send_activation")

    conda_activate(
        prefix=empty_conda_environment,
        working_dir=empty_conda_environment,
        env={"FOO": "set-in-project"},
    )

    assert "activated in a new shell" in capsys.readouterr().out

    assert mocked_spawn.call_args == mocker.call(
        command="/bin/sh",
        args=["-i"],
        cwd=empty_conda_environment,
        env={"FOO": "set-in-project"},
        echo=False,
    )
