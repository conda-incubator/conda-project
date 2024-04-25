# -*- coding: utf-8 -*-
# Copyright (C) 2022-2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import os
from pathlib import Path

import pytest

from conda_project.conda import (
    DEFAULT_PLATFORMS,
    call_conda,
    conda_activate,
    conda_info,
    conda_prefix,
    conda_run,
    current_platform,
    env_export,
    is_conda_env,
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
        "conda_project.conda.detect_shell",
        return_value=("/bin/sh", "/bin/sh"),
    )
    mocker.patch("conda_project.conda._send_activation")

    conda_activate(
        prefix=empty_conda_environment, working_dir=empty_conda_environment, env=None
    )

    assert "activated in a new shell" in capsys.readouterr().out

    assert mocked_spawn.call_args == mocker.call(
        command="/bin/sh", args=["-i"], cwd=empty_conda_environment, env={}, echo=True
    )


@pytest.mark.skipif(is_windows(), reason="On Windows we call subprocess")
def test_conda_activate_pexpect_with_variables(mocker, empty_conda_environment, capsys):
    mocked_spawn = mocker.patch("conda_project.conda.pexpect.spawn")
    mocker.patch(
        "conda_project.conda.detect_shell",
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
        echo=True,
    )


def test_conda_prefix_with_name(empty_conda_environment: Path, monkeypatch):
    monkeypatch.setenv("CONDA_ENVS_DIRS", str(empty_conda_environment.parent))

    prefix = conda_prefix(empty_conda_environment.name)
    assert prefix == empty_conda_environment


def test_conda_prefix_root():
    for env in "root", "base":
        prefix = conda_prefix(env)
        assert str(prefix) == os.environ["CONDA_ROOT"]


def test_conda_prefix_current_env():
    prefix = conda_prefix()
    assert str(prefix) == os.environ["CONDA_PREFIX"]


def test_conda_prefix_with_path(empty_conda_environment):
    prefix = conda_prefix(empty_conda_environment)
    assert prefix == empty_conda_environment


def test_conda_prefix_prefers_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CONDA_ENVS_DIRS", str(tmp_path / "global-envs"))

    create = ["create", "-n", "my-env", "--yes"]
    _ = call_conda(create)
    envs = conda_info()["envs"]
    assert str(tmp_path / "global-envs" / "my-env") in envs

    prefix = conda_prefix("my-env")
    assert prefix == tmp_path / "global-envs" / "my-env"

    create = ["create", "-p", str(tmp_path / "my-env"), "--yes"]
    _ = call_conda(create)

    prefix = conda_prefix("my-env")
    assert prefix == tmp_path / "my-env"

    _ = call_conda(["env", "remove", "-n", "my-env"])


def test_conda_prefix_name_not_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CONDA_ENVS_DIRS", str(tmp_path / "global-envs"))

    with pytest.raises(ValueError):
        _ = conda_prefix("not-an-env")


def test_conda_prefix_path_not_found(tmp_path):
    with pytest.raises(ValueError):
        _ = conda_prefix(tmp_path)


def test_is_conda_env_path(empty_conda_environment: Path):
    assert is_conda_env(empty_conda_environment)


def test_is_conda_env_false(tmp_path):
    assert not is_conda_env(tmp_path)


@pytest.mark.slow
def test_env_export_from_history_with_versions(empty_conda_environment):
    _ = call_conda(["install", "openssl", "-p", empty_conda_environment, "-y"])

    env, lock = env_export(empty_conda_environment)
    assert env.platforms == list(DEFAULT_PLATFORMS)
    assert len(env.dependencies) == 1
    assert len(env.dependencies[0].split("::")) == 2
    assert len(env.dependencies[0].split("=")) == 2
    assert len(lock.package) > 1
    assert lock.metadata.content_hash.keys() == DEFAULT_PLATFORMS


@pytest.mark.slow
def test_env_export_from_history_without_versions(empty_conda_environment):
    _ = call_conda(["install", "openssl", "-p", empty_conda_environment, "-y"])

    env, lock = env_export(empty_conda_environment, pin_versions=False)
    assert env.platforms == list(DEFAULT_PLATFORMS)
    assert len(env.dependencies) == 1
    assert len(env.dependencies[0].split("::")) == 2
    assert len(env.dependencies[0].split("=")) == 1
    assert len(lock.package) > 1
    assert lock.metadata.content_hash.keys() == DEFAULT_PLATFORMS


@pytest.mark.slow
def test_env_export_from_history_without_versions_as_requested(empty_conda_environment):
    _ = call_conda(["install", "openssl=3", "-p", empty_conda_environment, "-y"])

    env, lock = env_export(empty_conda_environment, pin_versions=False)
    assert env.platforms == list(DEFAULT_PLATFORMS)
    assert len(env.dependencies) == 1
    assert len(env.dependencies[0].split("::")) == 2
    assert env.dependencies[0].split("=") == ["defaults::openssl", "3"]
    assert len(lock.package) > 1
    assert lock.metadata.content_hash.keys() == DEFAULT_PLATFORMS


@pytest.mark.slow
def test_env_export_from_history_with_pip(empty_conda_environment):
    _ = call_conda(
        ["install", "python=3.11", "pip", "-p", empty_conda_environment, "-y"]
    )
    _ = call_conda(["run", "-p", empty_conda_environment, "pip", "install", "requests"])

    env, lock = env_export(empty_conda_environment)
    assert len(env.dependencies[-1]["pip"]) == 1
    assert len([p for p in lock.package if p.manager == "pip"]) > 1


@pytest.mark.slow
def test_env_export_full(empty_conda_environment):
    _ = call_conda(["install", "openssl=3", "-p", empty_conda_environment, "-y"])

    env, lock = env_export(empty_conda_environment, from_history=False)
    assert env.platforms == [current_platform()]
    assert len(env.dependencies) == len(lock.package)
    assert lock.metadata.content_hash.keys() == {current_platform()}


@pytest.mark.slow
def test_env_export_full_with_pip(empty_conda_environment):
    _ = call_conda(
        ["install", "python=3.11", "pip", "-p", empty_conda_environment, "-y"]
    )
    _ = call_conda(["run", "-p", empty_conda_environment, "pip", "install", "requests"])

    env, lock = env_export(empty_conda_environment, from_history=False)
    assert len(env.dependencies[-1]["pip"]) == len(
        [p for p in lock.package if p.manager == "pip"]
    )


@pytest.mark.slow
def test_env_export_all_requested(empty_conda_environment):
    _ = call_conda(["install", "ca-certificates", "-p", empty_conda_environment, "-y"])

    env, lock = env_export(empty_conda_environment, from_history=True)
    assert env.platforms == [current_platform()]
    assert len(env.dependencies) == len(lock.package)
    assert lock.metadata.content_hash.keys() == {current_platform()}


def test_env_export_empty_env(empty_conda_environment):
    env, lock = env_export(empty_conda_environment)

    assert env.platforms == list(DEFAULT_PLATFORMS)
    assert not env.dependencies
    assert not lock.package
    assert lock.metadata.content_hash.keys() == DEFAULT_PLATFORMS
