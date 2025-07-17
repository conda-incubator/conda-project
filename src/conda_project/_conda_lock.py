# Copyright (C) 2022-2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from pathlib import Path
from typing import AbstractSet, Dict, List, Optional, Sequence

import conda_lock
from conda_lock.conda_lock import (
    MetadataOption,
    PathLike,
    TKindAll,
    default_virtual_package_repodata,
)
from conda_lock.conda_lock import make_lock_files as _make_lock_files
from conda_lock.conda_lock import make_lock_spec as _make_lock_spec
from conda_lock.models.lock_spec import LockSpecification
from packaging.version import parse


def is_conda_lock_3() -> bool:
    return parse(conda_lock.__version__) >= parse("3.0.0")


def is_conda_lock_304() -> bool:
    return parse(conda_lock.__version__) >= parse("3.0.4")


if is_conda_lock_3():  # pragma: no cover
    from conda_lock.lookup import DEFAULT_MAPPING_URL  # pragma: no cover

if is_conda_lock_304():  # pragma: no cover
    from conda_lock.content_hash import compute_content_hashes  # pragma: no cover


def make_lock_spec(
    src_files: List[Path],
    channel_overrides: Optional[Sequence[str]] = None,
    pip_repository_overrides: Optional[Sequence[str]] = None,
    platform_overrides: Optional[Sequence[str]] = None,
    required_categories: Optional[AbstractSet[str]] = None,
) -> LockSpecification:
    if is_conda_lock_3():  # pragma: no cover
        spec = _make_lock_spec(  # type: ignore
            src_files=src_files,
            channel_overrides=channel_overrides,
            pip_repository_overrides=pip_repository_overrides,
            platform_overrides=platform_overrides,
            filtered_categories=required_categories,
            mapping_url=DEFAULT_MAPPING_URL,
        )
        return spec
    else:  # pragma: no cover
        spec = _make_lock_spec(  # type: ignore
            src_files=src_files,
            channel_overrides=channel_overrides,
            pip_repository_overrides=pip_repository_overrides,
            platform_overrides=platform_overrides,
            required_categories=required_categories,
            virtual_package_repo=default_virtual_package_repodata(),
        )
        return spec


def make_lock_files(
    *,
    conda: PathLike,
    src_files: List[Path],
    kinds: Sequence[TKindAll],
    lockfile_path: Optional[Path] = None,
    platform_overrides: Optional[Sequence[str]] = None,
    channel_overrides: Optional[Sequence[str]] = None,
    virtual_package_spec: Optional[Path] = None,
    update: Optional[Sequence[str]] = None,
    include_dev_dependencies: bool = True,
    filename_template: Optional[str] = None,
    filter_categories: bool = False,
    extras: Optional[AbstractSet[str]] = None,
    check_input_hash: bool = False,
    metadata_choices: AbstractSet[MetadataOption] = frozenset(),
    metadata_yamls: Sequence[Path] = (),
    with_cuda: Optional[str] = None,
    strip_auth: bool = False,
):
    if is_conda_lock_3():  # pragma: no cover
        _make_lock_files(  # pragma: no cover
            conda=conda,
            src_files=src_files,
            lockfile_path=lockfile_path,
            kinds=kinds,
            platform_overrides=platform_overrides,
            channel_overrides=channel_overrides,
            check_input_hash=check_input_hash,
            metadata_choices=metadata_choices,
            virtual_package_spec=virtual_package_spec,
            update=update,
            include_dev_dependencies=include_dev_dependencies,
            filename_template=filename_template,
            filter_categories=filter_categories,
            extras=extras,
            metadata_yamls=metadata_yamls,
            with_cuda=with_cuda,
            strip_auth=strip_auth,
            mapping_url=DEFAULT_MAPPING_URL,
        )
    else:  # pragma: no cover
        _make_lock_files(  # type: ignore; pragma: no cover
            conda=conda,
            src_files=src_files,
            lockfile_path=lockfile_path,
            kinds=kinds,
            platform_overrides=platform_overrides,
            channel_overrides=channel_overrides,
            check_input_hash=check_input_hash,
            metadata_choices=metadata_choices,
            virtual_package_spec=virtual_package_spec,
            update=update,
            include_dev_dependencies=include_dev_dependencies,
            filename_template=filename_template,
            filter_categories=filter_categories,
            extras=extras,
            metadata_yamls=metadata_yamls,
            with_cuda=with_cuda,
            strip_auth=strip_auth,
        )


def lock_spec_content_hashes(spec: LockSpecification) -> Dict[str, str]:
    if is_conda_lock_304():  # pragma: no cover
        return compute_content_hashes(
            spec, virtual_package_repo=default_virtual_package_repodata()
        )
    elif is_conda_lock_3():  # pragma: no cover
        return spec.content_hash(  # pragma: no cover
            virtual_package_repo=default_virtual_package_repodata()
        )
    else:  # pragma: no cover
        return spec.content_hash()  # pragma: no cover
