# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

from .project import CondaProject, load_project
