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
            print(f"{e.__class__.__name__}: {e}", file=sys.stderr)
            return 1

    return wrapper


@handle_errors
def create(args: Namespace) -> None:
    project = CondaProject.create(
        args.directory,
        args.name,
        args.dependencies,
        args.channel,
        args.platforms.split(","),
        [] if args.conda_configs is None else args.conda_configs.split(","),
        not args.no_lock,
        verbose=True,
    )

    if args.prepare:
        project.prepare(verbose=True)


@handle_errors
def lock(args: Namespace) -> None:
    project = CondaProject(args.directory)
    if args.all:
        for _, env in project.environments:
            project.lock(environment=env, force=args.force, verbose=True)
    else:
        project.lock(force=args.force, environment=args.environment, verbose=True)


@handle_errors
def prepare(args: Namespace) -> None:
    project = CondaProject(args.directory)

    if args.all:
        for _, env in project.environments:
            project.prepare(environment=env, force=args.force, verbose=True)
    else:
        project.prepare(force=args.force, environment=args.environment, verbose=True)


@handle_errors
def clean(args: Namespace) -> None:
    project = CondaProject(args.directory)

    if args.all:
        for _, env in project.environments:
            project.clean(environment=env, verbose=True)
    else:
        project.clean(environment=args.environment, verbose=True)
