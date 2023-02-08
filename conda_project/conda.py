# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import os
import subprocess
from functools import lru_cache
from logging import Logger
from pathlib import Path
from typing import List
from typing import Optional

from .exceptions import CondaProjectError


CONDA_EXE = os.environ.get("CONDA_EXE", "conda")


def call_conda(
    args: List[str],
    condarc_path: Optional[Path] = None,
    verbose: bool = False,
    logger: Optional[Logger] = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
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
        raise CondaProjectError(
            f"Failed to run:\n  {print_cmd}\n{proc.stderr.strip()}"
        )

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
