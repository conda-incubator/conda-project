# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause


class CondaProjectError(Exception):
    pass


class CondaProjectLockFailed(CondaProjectError):
    pass


class CommandNotFoundError(CondaProjectError):
    pass
