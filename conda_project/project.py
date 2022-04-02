# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
import subprocess

CONDA_EXE = os.environ.get("CONDA_EXE", "conda")


def call_conda(args, env):
    subprocess.run(
        [CONDA_EXE] + args
    )


def load_project(directory=None):
    project = CondaProject(directory)
    return project


class CondaProject:
    def __init__(self, directory=None):
        self.directory = os.path.normcase(os.path.abspath(directory))

    def default_env(self):
        return os.path.join(self.directory, 'envs', 'default')

    def prepare(self):
        default_env = self.default_env()
        call_conda(
            ['env', 'create', '-p', default_env]
        )
        return default_env

    def clean(self):
        call_conda(
            ['env', 'remove', '-p', self.default_env()]
        )
