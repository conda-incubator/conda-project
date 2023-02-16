# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
from functools import lru_cache
from logging import Logger
from pathlib import Path
from typing import Dict, List, NoReturn, Optional

import pexpect
import shellingham
from conda_lock._vendor.conda.utils import wrap_subprocess_call

from .exceptions import CondaProjectError
from .utils import execvped, is_windows

CONDA_EXE = os.environ.get("CONDA_EXE", "conda")
CONDA_ROOT = os.environ.get("CONDA_ROOT")
CONDA_PREFIX = os.environ.get("CONDA_PREFIX")


def call_conda(
    args: List[str],
    condarc_path: Optional[Path] = None,
    verbose: bool = False,
    logger: Optional[Logger] = None,
    variables: Optional[dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """Call conda CLI with subprocess.run"""

    parent_process_env = os.environ.copy()

    variables = {} if variables is None else variables
    env = {**variables, **parent_process_env}

    if condarc_path is not None:
        if logger is not None:
            logger.info(f"setting CONDARC env variable to {condarc_path}")
        env["CONDARC"] = str(condarc_path)

    cmd = [CONDA_EXE] + args

    if verbose:
        stdout = None
    else:
        stdout = subprocess.PIPE

    if logger is not None:
        logger.info(f'running conda command: {" ".join(cmd)}')

    proc = subprocess.run(
        cmd, env=env, stdout=stdout, stderr=subprocess.PIPE, encoding="utf-8"
    )

    if proc.returncode != 0:
        print_cmd = " ".join(cmd)
        raise CondaProjectError(f"Failed to run:\n  {print_cmd}\n{proc.stderr.strip()}")

    return proc


def conda_info():
    proc = call_conda(["info", "--json"])
    parsed = json.loads(proc.stdout)
    return parsed


@lru_cache()
def current_platform() -> str:
    """Load the current platform by calling conda info."""
    info = conda_info()
    return info.get("platform")


def conda_run(
    cmd: str,
    prefix: Path,
    working_dir: Path,
    env: Optional[Dict[str, str]] = None,
    extra_args: Optional[List[str]] = None,
) -> NoReturn:
    extra_args = [] if extra_args is None else extra_args
    arguments = shlex.split(cmd) + extra_args

    _, (shell, *args) = wrap_subprocess_call(
        root_prefix=CONDA_ROOT,
        prefix=str(prefix),
        dev_mode=False,
        debug_wrapper_scripts=False,
        arguments=arguments,
        use_system_tmp_path=True,
    )

    env = {} if env is None else env

    if not is_windows():
        args = ["-c", *args]

    execvped(file=shell, args=args, env=env, cwd=working_dir)


def _send_activation(child_shell, prefix):
    def sigwinch_passthrough(sig, data):
        if not child_shell.closed:
            t = os.get_terminal_size()
            child_shell.setwinsize(t.lines, t.columns)

    t = os.get_terminal_size()
    child_shell.setwinsize(t.lines, t.columns)
    signal.signal(signal.SIGWINCH, sigwinch_passthrough)
    child_shell.sendline(f"conda activate {prefix}")
    child_shell.interact()
    child_shell.close()


def conda_activate(prefix: Path, working_dir: Path, env: Optional[Dict] = None):
    env = {} if env is None else env

    try:
        shell_name, shell_path = shellingham.detect_shell()
    except shellingham.ShellDetectionFailure:
        if os.name == "posix":
            shell_name = shell_path = os.environ.get("SHELL", "/bin/sh")
        elif os.name == "nt":
            shell_name = shell_path = os.environ.get("COMSPEC", "cmd.exe")
        else:
            raise RuntimeError("Could not determine an appropriate shell to activate.")

    args = []
    if is_windows():
        if shell_name in ["powershell", "pwsh"]:
            conda_hook = str(Path(CONDA_ROOT) / "shell" / "condabin" / "conda-hook.ps1")
            args = [
                "-ExecutionPolicy",
                "ByPass",
                "-NoExit",
                conda_hook,
                ";",
                "conda",
                "activate",
                str(prefix),
            ]
        elif shell_name == "cmd":
            activate_bat = str(Path(CONDA_ROOT) / "Scripts" / "activate.bat")
            args = ["/K", activate_bat, str(prefix)]
    else:
        args = ["-i"]

    activate_message = (
        f"## Project environment {prefix.name} activated in a new shell.\n"
        f"## Exit this shell to de-activate."
    )
    print(activate_message)

    if is_windows():
        subprocess.run([shell_path, *args], cwd=working_dir, env=env)
    else:
        child_shell = pexpect.spawn(
            command=shell_path, args=args, cwd=working_dir, env=env, echo=False
        )

        _send_activation(child_shell, prefix)
