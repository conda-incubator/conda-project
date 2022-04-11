# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .exceptions import CondaProjectError

CONDA_EXE = os.environ.get("CONDA_EXE", "conda")


def call_conda(args: list[str], condarc_path: Path = None, verbose: bool = False) -> subprocess.Popen:
    env = os.environ.copy()
    if condarc_path is not None:
        env['CONDARC'] = str(condarc_path)

    cmd = [CONDA_EXE] + args

    if verbose:
        stdout = None
    else:
        stdout = subprocess.PIPE

    proc = subprocess.run(
        cmd,
        env=env,
        stdout=stdout,
        stderr=subprocess.PIPE,
        encoding='utf-8'
    )

    if proc.returncode != 0:
        print_cmd = ' '.join(cmd)
        raise CondaProjectError(f'Failed to run:\n  {print_cmd}\n{proc.stderr.strip()}')

    return proc
