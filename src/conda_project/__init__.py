# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import importlib.metadata

__version__ = importlib.metadata.version("conda-project")

# flake8: noqa
from .exceptions import CondaProjectError
from .project import CondaProject
