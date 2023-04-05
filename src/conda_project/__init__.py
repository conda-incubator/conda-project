# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"

# flake8: noqa
from .exceptions import CondaProjectError
from .project import CondaProject
