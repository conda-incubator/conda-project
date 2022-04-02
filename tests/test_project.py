# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
import pytest
import subprocess

from conda_project.project import CondaProject, CondaProjectError


def test_conda_project_init_no_env_yml(tmpdir):
    with pytest.raises(CondaProjectError) as excinfo:
        CondaProject(tmpdir)
    assert 'No Conda environment.yml or environment.yaml file was found' in str(excinfo.value)


@pytest.mark.parametrize('env_fn', ['environment.yml', 'environment.yaml'])
def test_project_init_directory(monkeypatch, tmpdir, env_fn):
    contents = """name: test
dependencies: []
"""
    env_file = tmpdir.join(env_fn)
    env_file.write(contents)

    monkeypatch.chdir(tmpdir)
    project = CondaProject()
    assert project.directory == tmpdir


@pytest.mark.parametrize('env_fn', ['environment.yml', 'environment.yaml'])
def test_prepare_no_dependencies(monkeypatch, tmpdir, env_fn):
    contents = """name: test
dependencies: []
"""
    env_file = tmpdir.join(env_fn)
    env_file.write(contents)

    monkeypatch.chdir(tmpdir)
    project = CondaProject('.')
    assert project.directory == tmpdir

    env_dir = project.prepare()
    assert env_dir == os.path.join(tmpdir, 'envs', 'default')

    conda_history = os.path.join(env_dir, 'conda-meta', 'history')
    assert os.path.exists(conda_history)


@pytest.mark.parametrize('env_fn', ['environment.yml', 'environment.yaml'])
def test_project_condarc(tmpdir, capsys, env_fn):
    env_yaml = """name: test
dependencies: []
"""
    env_file = tmpdir.join(env_fn)
    env_file.write(env_yaml)

    condarc = "channels: [__conda-project-test]\n"
    condarc_file = tmpdir.join('.condarc')
    condarc_file.write(condarc)

    project = CondaProject(tmpdir, capture_output=True)

    proc = project._call_conda(['config', '--show', 'channels'])
    channels = proc.stdout.splitlines()
    assert channels[1] == '  - __conda-project-test'


@pytest.mark.slow
@pytest.mark.parametrize('env_fn', ['environment.yml', 'environment.yaml'])
def test_prepare_and_clean(tmpdir, env_fn):
    contents = """name: test
dependencies:
  - python=3.8
"""
    env_file = tmpdir.join(env_fn)
    env_file.write(contents)

    project = CondaProject(tmpdir)
    env_dir = project.prepare()
    assert env_dir == os.path.join(tmpdir, 'envs', 'default')

    conda_history = os.path.join(env_dir, 'conda-meta', 'history')
    assert os.path.exists(conda_history)
    with open(conda_history) as f:
        assert "# update specs: ['python=3.8']" in f.read()

    with pytest.raises(CondaProjectError) as excinfo:
        project.prepare()
    assert 'prefix already exists' in str(excinfo.value)

    project.prepare(force=True)

    project.clean()
    assert not os.path.exists(conda_history)
