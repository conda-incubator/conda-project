# Copyright (C) 2022-2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from pathlib import Path

import pytest

from conda_project.exceptions import CondaProjectError
from conda_project.project import CondaProject
from conda_project.utils import is_windows

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


@pytest.fixture(scope="function", autouse=True)
def chdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def test_extract_top_level_dir():
    archive = ASSETS_DIR / "top-level-dir.tar.gz"
    project = CondaProject.from_archive(fn=archive)

    assert project.directory.name == "my-project"

    dir_contents = sorted(list(project.directory.glob("**/*")))
    assert dir_contents == sorted([project.directory / p for p in PROJECT_CONTENTS])


def test_extract_top_level_dir_rename():
    archive = ASSETS_DIR / "top-level-dir.tar.gz"
    project = CondaProject.from_archive(
        fn=archive, output_directory="extracted-project"
    )

    assert project.directory.name == "extracted-project"

    dir_contents = sorted(list(project.directory.glob("**/*")))
    assert dir_contents == sorted(
        [("extracted-project" / p).resolve() for p in PROJECT_CONTENTS]
    )


def test_extract_no_top_level_dir():
    archive = ASSETS_DIR / "no-top-level-dir.tar.gz"
    project = CondaProject.from_archive(fn=archive)

    assert project.directory.name == "no-top-level-dir"

    dir_contents = sorted(list(project.directory.glob("**/*")))
    assert dir_contents == sorted(
        [("no-top-level-dir" / p).resolve() for p in PROJECT_CONTENTS]
    )


def test_extract_no_top_level_dir_rename():
    archive = ASSETS_DIR / "no-top-level-dir.tar.gz"
    project = CondaProject.from_archive(
        fn=archive, output_directory="extracted-project"
    )

    assert project.directory.name == "extracted-project"

    dir_contents = sorted(list(project.directory.glob("**/*")))
    assert dir_contents == sorted(
        [("extracted-project" / p).resolve() for p in PROJECT_CONTENTS]
    )


def test_extract_unnamed_top_level_dir():
    archive = ASSETS_DIR / "unnamed-top-level-dir.tar.gz"
    project = CondaProject.from_archive(fn=archive)

    assert project.directory.name == "unnamed-top-level-dir"

    dir_contents = sorted(list(project.directory.glob("**/*")))
    assert dir_contents == sorted(
        [("unnamed-top-level-dir" / p).resolve() for p in PROJECT_CONTENTS]
    )


def test_extract_unnamed_top_level_dir_rename():
    archive = ASSETS_DIR / "unnamed-top-level-dir.tar.gz"
    project = CondaProject.from_archive(
        fn=archive, output_directory="extracted-project"
    )

    assert project.directory.name == "extracted-project"

    dir_contents = sorted(list(project.directory.glob("**/*")))
    assert dir_contents == sorted(
        [("extracted-project" / p).resolve() for p in PROJECT_CONTENTS]
    )


def test_extract_fails_relative_paths():
    archive = ASSETS_DIR / "relative-paths.tar.gz"

    with pytest.raises(CondaProjectError):
        _ = CondaProject.from_archive(fn=archive)


def test_archive_storage_options(mocker):
    from conda_project.project import fsspec

    mocked_open_files = mocker.spy(fsspec, "open_files")

    fn = ASSETS_DIR / "top-level-dir.tar.gz"
    _ = CondaProject.from_archive(
        f"file:///{fn}", storage_options={"key1": "valueA", "key2": "valueB"}
    )

    assert mocked_open_files.call_args_list[0].kwargs == {
        "file": {"key1": "valueA", "key2": "valueB"}
    }
    assert "simplecache" in mocked_open_files.call_args_list[0].args[0]


def test_archive_path_expanduser(mocker):
    from pathlib import Path

    expanduser = mocker.spy(Path, "expanduser")

    archive = "~__a-conda-project-user__/project.tar.gz"
    if is_windows():
        with pytest.raises(FileNotFoundError):
            _ = CondaProject.from_archive(fn=archive)
    else:
        with pytest.raises(RuntimeError):
            _ = CondaProject.from_archive(fn=archive)

    assert expanduser.call_count == 2


def test_archive_output_directory_expanduser(mocker):
    from pathlib import Path

    expanduser = mocker.spy(Path, "expanduser")

    archive = ASSETS_DIR / "top-level-dir.tar.gz"

    output_directory = "~__a-conda-project-user__/project"
    if is_windows():
        _ = CondaProject.from_archive(fn=archive, output_directory=output_directory)
        assert expanduser.call_count == 3
    else:
        with pytest.raises(RuntimeError):
            _ = CondaProject.from_archive(fn=archive, output_directory=output_directory)
        assert expanduser.call_count == 1
