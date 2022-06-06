# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import sys
from argparse import Namespace
from functools import wraps
from typing import Any, Callable

from ..exceptions import CondaProjectError
from ..project import CondaProject


def handle_errors(func: Callable[[Namespace], Any]) -> Callable[[Namespace], int]:
    """Wrap a subcommand function to catch exceptions and return an appropriate error code."""

    @wraps(func)
    def wrapper(args: Namespace) -> int:
        try:
            func(args)
            return 0
        except CondaProjectError as e:
            print(f'{e.__class__.__name__}: {e}', file=sys.stderr)
            return 1

    return wrapper


@handle_errors
def lock(args: Namespace) -> None:
    project = CondaProject(args.directory)
    project.lock(force=args.force, verbose=True)


@handle_errors
def prepare(args: Namespace) -> None:
    project = CondaProject(args.directory)
    project.prepare(force=args.force, verbose=True)


@handle_errors
def clean(args: Namespace) -> None:
    project = CondaProject(args.directory)
    project.clean(verbose=True)
