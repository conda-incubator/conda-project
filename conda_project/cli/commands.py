# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import sys
from functools import wraps

from ..project import CondaProject, CondaProjectError


def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
            return 0
        except CondaProjectError as e:
            print(e, file=sys.stderr)
            return 1
    return wrapper


@handle_errors
def prepare(args):
    project = CondaProject(args.directory, capture_output=False)
    project.prepare(args.force)


@handle_errors
def clean(args):
    project = CondaProject(args.directory, capture_output=False)
    project.clean()
