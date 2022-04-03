# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
import subprocess

CONDA_EXE = os.environ.get("CONDA_EXE", "conda")


class CondaError(Exception):
    pass


def call_conda(args, condarc_path=None, verbose=False):
    env = {}
    if condarc_path is not None:
        env['CONDARC'] = condarc_path

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
        raise CondaError(f'Failed to run "{print_cmd}"\n{proc.stderr.strip()}')

    return proc
