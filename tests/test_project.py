# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
import pytest

from conda_project.project import CondaProject
from conda_project.exceptions import CondaProjectError


def test_conda_project_init_no_env_yml(tmpdir):
    with pytest.raises(CondaProjectError) as excinfo:
        CondaProject(tmpdir)
    assert 'No Conda environment.yml or environment.yaml file was found' in str(excinfo.value)


def test_project_init_expands_cwd(monkeypatch, project_directory):
    tmpdir = project_directory()
    monkeypatch.chdir(tmpdir)

    project = CondaProject()
    assert project.directory == tmpdir
    assert project.environment_file


def test_project_init_path(project_directory):
    tmpdir = project_directory()

    project = CondaProject(tmpdir)
    assert project.environment_file


def test_prepare_no_dependencies(project_directory):
    env_yaml = """name: test
dependencies: []
"""
    tmpdir = project_directory(env_yaml=env_yaml)
    project = CondaProject(tmpdir)
    assert os.path.samefile(project.directory, tmpdir)

    env_dir = project.prepare()
    assert os.path.samefile(env_dir, os.path.join(tmpdir, 'envs', 'default'))

    conda_history = os.path.join(env_dir, 'conda-meta', 'history')
    assert os.path.exists(conda_history)


@pytest.mark.slow
def test_prepare_and_clean(project_directory):
    env_yaml = """name: test
dependencies:
  - python=3.8
"""
    tmpdir = project_directory(env_yaml=env_yaml)

    project = CondaProject(tmpdir)
    env_dir = project.prepare()
    assert os.path.samefile(env_dir, os.path.join(tmpdir, 'envs', 'default'))

    conda_history = os.path.join(env_dir, 'conda-meta', 'history')
    assert os.path.exists(conda_history)
    with open(conda_history) as f:
        assert "# update specs: ['python=3.8']" in f.read()
    conda_history_mtime = os.path.getmtime(conda_history)

    project.prepare()
    assert conda_history_mtime == os.path.getmtime(conda_history)

    project.prepare(force=True)
    assert conda_history_mtime < os.path.getmtime(conda_history)

    project.clean()
    assert not os.path.exists(conda_history)
