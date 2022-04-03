# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
from re import sub
import subprocess

CONDA_EXE = os.environ.get("CONDA_EXE", "conda")

ENVIRONMENT_YAML_FILENAMES = ('environment.yml', 'environment.yaml')


class CondaProjectError(Exception):
    pass


class CondaProject:
    def __init__(self, directory=None, capture_output=True):
        self.capture_output = capture_output

        if directory is None:
            directory = '.'
        self.directory = os.path.normcase(os.path.abspath(directory))

        for fn in ENVIRONMENT_YAML_FILENAMES:
            fn = os.path.join(self.directory, fn)
            if os.path.exists(fn):
                self.environment_file = fn
                break
        else:
            raise CondaProjectError(f'No Conda environment.yml or environment.yaml file was found in {self.directory}.')

    def _call_conda(self, args):
        env = {}
        condarc = os.path.join(self.directory, '.condarc')
        if os.path.exists(condarc):
            env['CONDARC'] = condarc

        stderr = subprocess.PIPE
        if self.capture_output:
            stdout = subprocess.PIPE
        else:
            stdout = None

        cmd = [CONDA_EXE] + args
        proc = subprocess.run(
            cmd,
            env=env,
            # stdout=stdout,
            # stderr=stderr,
            encoding='utf-8'
        )

        if proc.returncode != 0:
            print_cmd = ' '.join(cmd)
            raise CondaProjectError(f'Failed to run "{print_cmd}"\n{proc.stderr.strip()}')

        return proc

    def default_env(self):
        return os.path.join(self.directory, 'envs', 'default')

    def prepare(self, force=False):
        default_env = self.default_env()
        conda_meta = os.path.join(default_env, 'conda-meta', 'history')
        force = '--force' if force else ''
        if os.path.exists(conda_meta) and not force:
            return default_env
        else:
            _ = self._call_conda(
                ['env', 'create', '-f', self.environment_file, '-p', default_env, force]
            )
            return default_env

    def clean(self):
        _ = self._call_conda(
            ['env', 'remove', '-p', self.default_env()]
        )
