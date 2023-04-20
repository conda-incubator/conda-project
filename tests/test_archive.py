# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from pathlib import Path

import pytest

from conda_project.exceptions import CondaProjectError
from conda_project.project import CondaProject

ASSETS_DIR = Path(__file__).parents[0] / "assets"

PROJECT_CONTENTS = [
    Path(".condarc"),
    Path(".env"),
    Path("README.md"),
    Path("conda-lock.default.yml"),
    Path("conda-project.yml"),
    Path("data"),
    Path("data/file"),
    Path("environment.yml"),
]


def test_extract_top_level_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    archive = ASSETS_DIR / "top-level-dir.tar.gz"
    project = CondaProject.from_archive(fn=archive)

    assert project.directory.name == "my-project"

    dir_contents = sorted(list(project.directory.glob("**/*")))
    assert dir_contents == [project.directory / p for p in PROJECT_CONTENTS]


def test_extract_top_level_dir_rename(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    archive = ASSETS_DIR / "top-level-dir.tar.gz"
    project = CondaProject.from_archive(
        fn=archive, output_directory="extracted-project"
    )

    assert project.directory.name == "extracted-project"

    dir_contents = sorted(list(project.directory.glob("**/*")))
    assert dir_contents == [
        ("extracted-project" / p).resolve() for p in PROJECT_CONTENTS
    ]


def test_extract_no_top_level_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    archive = ASSETS_DIR / "no-top-level-dir.tar.gz"
    project = CondaProject.from_archive(fn=archive)

    assert project.directory.name == "no-top-level-dir"

    dir_contents = sorted(list(project.directory.glob("**/*")))
    assert dir_contents == [
        ("no-top-level-dir" / p).resolve() for p in PROJECT_CONTENTS
    ]


def test_extract_no_top_level_dir_rename(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    archive = ASSETS_DIR / "no-top-level-dir.tar.gz"
    project = CondaProject.from_archive(
        fn=archive, output_directory="extracted-project"
    )

    assert project.directory.name == "extracted-project"

    dir_contents = sorted(list(project.directory.glob("**/*")))
    assert dir_contents == [
        ("extracted-project" / p).resolve() for p in PROJECT_CONTENTS
    ]


def test_extract_unnamed_top_level_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    archive = ASSETS_DIR / "unnamed-top-level-dir.tar.gz"
    project = CondaProject.from_archive(fn=archive)

    assert project.directory.name == "unnamed-top-level-dir"

    dir_contents = sorted(list(project.directory.glob("**/*")))
    assert dir_contents == [
        ("unnamed-top-level-dir" / p).resolve() for p in PROJECT_CONTENTS
    ]


def test_extract_unnamed_top_level_dir_rename(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    archive = ASSETS_DIR / "unnamed-top-level-dir.tar.gz"
    project = CondaProject.from_archive(
        fn=archive, output_directory="extracted-project"
    )

    assert project.directory.name == "extracted-project"

    dir_contents = sorted(list(project.directory.glob("**/*")))
    assert dir_contents == [
        ("extracted-project" / p).resolve() for p in PROJECT_CONTENTS
    ]


def test_extract_fails_relative_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    archive = ASSETS_DIR / "relative-paths.tar.gz"

    with pytest.raises(CondaProjectError):
        _ = CondaProject.from_archive(fn=archive)


def test_archive_storage_options(mocker):
    from conda_project.project import fsspec

    open_files = mocker.spy(fsspec, "open_files")

    fn = ASSETS_DIR / "top-level-dir.tar.gz"
    _ = CondaProject.from_archive(
        f"file:///{fn}", storage_options={"key1": "valueA", "key2": "valueB"}
    )

    assert open_files.call_args_list[0].kwargs == {
        "file": {"key1": "valueA", "key2": "valueB"}
    }
