# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import os
from pathlib import Path

from .conda import call_conda
from .exceptions import CondaProjectError

ENVIRONMENT_YAML_FILENAMES = ('environment.yml', 'environment.yaml')


class CondaProject:
    """A project managed by `conda-project`.

    Attributes:
        directory: The project base directory
        condarc: A path to the local `.condarc` file. Defaults to `<directory>/.condarc`.
        environment_file: A path to the environment file.

    Args:
        directory: The project base directory.

    Raises:
        CondaProjectError: If no suitable environment file is found.

    """
    def __init__(self, directory: Path | str = '.'):
        self.directory = Path(directory).resolve()

        self.condarc = os.path.join(self.directory, '.condarc')

        for fn in ENVIRONMENT_YAML_FILENAMES:
            fn = os.path.join(self.directory, fn)
            if os.path.exists(fn):
                self.environment_file = fn
                break
        else:
            raise CondaProjectError(f'No Conda environment.yml or environment.yaml file was found in {self.directory}.')

    def default_env(self):
        return os.path.join(self.directory, 'envs', 'default')

    def prepare(self, force=False, verbose=False):
        default_env = self.default_env()
        conda_meta = os.path.join(default_env, 'conda-meta', 'history')
        force = '--force' if force else ''
        if os.path.exists(conda_meta) and not force:
            return default_env
        else:
            _ = call_conda(
                ['env', 'create', '-f', self.environment_file, '-p', default_env, force],
                condarc_path=self.condarc,
                verbose=verbose
            )
            return default_env

    def clean(self, verbose=False):
        _ = call_conda(
            ['env', 'remove', '-p', self.default_env()],
            condarc_path=self.condarc,
            verbose=verbose
        )
