# -*- coding: utf-8 -*-
# Copyright (C) 2022-2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
from contextlib import nullcontext
from functools import lru_cache
from logging import Logger
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, NoReturn, Optional, Tuple, Union, cast

import conda_lock._vendor.conda.gateways.logging  # noqa: F401
import pexpect
from conda_lock._vendor.conda.core.prefix_data import PrefixData, PrefixRecord
from conda_lock._vendor.conda.models.channel import Channel
from conda_lock._vendor.conda.utils import wrap_subprocess_call
from conda_lock.conda_lock import (
    default_virtual_package_repodata,
    make_lock_spec,
    parse_conda_lock_file,
)
from conda_lock.lockfile.v2prelim.models import Lockfile

from .exceptions import CondaProjectError
from .project_file import EnvironmentYaml, UniqueOrderedList
from .utils import Spinner, detect_shell, execvped, is_windows

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


def is_conda_env(prefix: Path) -> bool:
    return (prefix / "conda-meta" / "history").exists()


def conda_prefix(env: Optional[Union[str, Path]] = None) -> Union[Path, None]:
    """Return the path to a conda environment"""

    if env is None:
        return Path(os.environ["CONDA_PREFIX"]).resolve()

    elif env in ("base", "root"):
        return Path(os.environ["CONDA_ROOT"]).resolve()

    else:
        env = Path(env) if isinstance(env, str) else env

        if is_conda_env(env):
            return env.resolve()

        else:
            for d in conda_info()["envs_dirs"]:
                p = Path(d) / env
                if is_conda_env(p):
                    return p.resolve()
            else:
                return None


def env_export(
    prefix: Path,
    from_history: bool = True,
    pin_versions: bool = True,
    verbose: bool = False,
) -> Tuple[EnvironmentYaml, Lockfile]:
    """Create an environment.yml spec and lockfile from an existing environment"""

    pd = PrefixData(prefix, pip_interop_enabled=True)
    pkgs = cast(List[PrefixRecord], pd.iter_records())

    channels: List[Channel] = []
    dependencies: List[Union[str, Dict[str, List[str]]]] = []
    pip: List[str] = []

    n_conda = 0
    n_pip = 0
    for p in pkgs:
        if p.schannel == "pypi":
            n_pip += 1
            if from_history:
                for fn in p.files:
                    fn = prefix / Path(fn)
                    if fn.name == "REQUESTED":
                        pip.append(f"{p.name}=={p.version}")
                        break
            else:
                pip.append(f"{p.name}=={p.version}")
            continue

        n_conda += 1

        if from_history and p.requested_spec == "None":
            continue

        if from_history and pin_versions:
            spec = f"{p.schannel}::{p.name}={p.version}"
        elif from_history and (not pin_versions):
            spec = f"{p.schannel}::{p.requested_spec}"
        else:
            spec = f"{p.schannel}::{p.name}={p.version}={p.build}"
        dependencies.append(spec)

        channels.append(p.channel)

    full_export = (not from_history) or (
        len(pip) + len(dependencies) == n_conda + n_pip
    )
    empty = n_conda + n_pip == 0

    if pip:
        dependencies.append({"pip": pip})

    if full_export:
        subdirs = set(c.subdir for c in channels)
        subdirs.discard("pypi")
        subdirs.discard("noarch")
        if not subdirs:
            platforms = [current_platform()]
        else:
            platforms = list(subdirs)
    else:
        platforms = DEFAULT_PLATFORMS

    channel_names = UniqueOrderedList(
        [Channel.from_url(url).canonical_name for url in conda_info()["channels"]]
    )

    environment = EnvironmentYaml(
        name=prefix.name,
        channels=channel_names,
        dependencies=dependencies,
        platforms=DEFAULT_PLATFORMS if empty else platforms,
        prefix=prefix,
    )
    with Spinner("Constructing lockfile") if verbose else nullcontext():
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)

            requested = tmp / "requested.yml"
            environment.yaml(requested)
            spec = make_lock_spec(
                src_files=[requested],
                virtual_package_repo=default_virtual_package_repodata(),
            )

            if full_export or empty:
                exported = requested
            else:
                exported = tmp / "exported.yml"
                call_conda(
                    ["env", "export", "-p", str(prefix), "--file", str(exported)]
                )

            lock = tmp / "conda-lock.yml"
            call_conda(
                [
                    "lock",
                    "-f",
                    str(exported),
                    "--lockfile",
                    str(lock),
                    "-p",
                    current_platform(),
                ]
            )
            lock_content = parse_conda_lock_file(lock)
            lock_content.metadata.content_hash = spec.content_hash()
            lock_content.metadata.sources = ["environment.yml"]

    return environment, lock_content


def conda_info():
    proc = call_conda(["info", "--json"])
    parsed = json.loads(proc.stdout)
    return parsed


@lru_cache()
def current_platform() -> str:
    """Load the current platform by calling conda info."""
    info = conda_info()
    return info.get("platform")


DEFAULT_PLATFORMS = set(["osx-64", "win-64", "linux-64", current_platform()])


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


def _send_activation(child_shell: pexpect.spawn, prefix):
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

    shell_path, shell_name = detect_shell()

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
            command=shell_path, args=args, cwd=working_dir, env=env, echo=True
        )

        _send_activation(child_shell, prefix)

        # local_dependencies = {}
        # for dep in p.depends:
        #     matchspec = MatchSpec(dep)
        #     name = matchspec.name
        #     version = (
        #         matchspec.version.spec_str if matchspec.version is not None else ""
        #     )
        #     local_dependencies[name] = version

        # if p.schannel == "pypi":
        #     if "WHEEL" in str(p.package_type):
        #         for fn in p.files:
        #             fn = prefix / Path(fn)
        #             if fn.name == "WHEEL":
        #                 with fn.open() as f:
        #                     data = f.readlines()
        #                 lines = [line for line in data if line.startswith("Tag")]
        #                 if lines:
        #                     tag = lines[0].split(":", maxsplit=1)[1].strip()
        #                     wheel = f"{p.name}-{p.version}-{tag}.whl"
        #                     parsed = parse_wheel_filename(wheel)
        #                     url = f"https://files.pythonhosted.org/packages/{parsed.python_tags[0]}/"
        #                           f"{parsed.project[0]}/{parsed.project}/{p.name}-{p.version}-{tag}.whl"
        #                 break
        #     else:
        #         url = f"https://pypi.io/packages/source/{p.name[0]}/{p.name}/{p.name}-{p.version}.tar.gz"
        # else:
        #     url = str(p.url)

        # locked.append(LockedDependency(
        #     name=p.name,
        #     version=p.version,
        #     manager="pip" if p.schannel == "pypi" else "conda",
        #     platform="unknown",
        #     dependencies=local_dependencies,
        #     url=url,
        #     hash=HashModel(
        #         md5=p.get("md5"),
        #         sha256=p.get("sha256")
        #     ),
        # ))
    # lock_content = Lockfile(
    #     package=locked,
    #     metadata=LockMeta(
    #         content_hash=spec.content_hash(),
    #         channels=list(),
    #         platforms=[current_platform()],
    #         sources=["environment.yml"],
    #     ),
    # )


# def requested_packages(prefix: Path, with_version: bool = True) -> EnvironmentYaml:
#     proc = call_conda(["env", "export", "--from-history", "-p", str(prefix), "--json"])
#     requested = json.loads(proc.stdout)

#     proc = call_conda(["env", "export", "-p", str(prefix), "--json"])
#     full = json.loads(proc.stdout)

#     if with_version:
#         versioned_dependencies = []

#         dependencies = {}
#         for d in requested["dependencies"]:
#             split = d.split("::", maxsplit=1)
#             if len(split) == 1:
#                 name = split[0].split("=")[0]
#                 dependencies[name] = ""
#             else:
#                 channel, name = split
#                 dependencies[name.split("=")[0]] = f"{channel}::"

#         for d in full["dependencies"]:
#             if isinstance(d, str):
#                 name, version, _ = d.split("=")
#                 if name in dependencies:
#                     prefix = dependencies[name]
#                     versioned_dependencies.append(f"{prefix}{name}={version}")

#         requested["dependencies"] = versioned_dependencies

#     pip_pkgs = [p for p in full["dependencies"] if isinstance(p, dict) and "pip" in p]
#     if pip_pkgs:
#         pip_pkgs = [p for p in pip_pkgs[0]["pip"] if not p.startswith("anaconda")]
#         requested["dependencies"].append({"pip": pip_pkgs})

#     environment = EnvironmentYaml(**requested)
#     return environment
