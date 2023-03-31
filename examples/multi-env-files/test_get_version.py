# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from print_version import get_version


def test_get_version():
    v = get_version()

    assert isinstance(v, tuple)
