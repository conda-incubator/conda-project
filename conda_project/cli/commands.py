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
            ret = func(args)
            if ret:
                return 0
            else:
                return 1
        except CondaProjectError as e:
            print(f"{e.__class__.__name__}: {e}", file=sys.stderr)
            return 1

    return wrapper


@handle_errors
def create(args: Namespace) -> bool:
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
        project.default_environment.prepare(verbose=True)

    return True


@handle_errors
def lock(args: Namespace) -> bool:
    project = CondaProject(args.directory)

    if args.environment:
        to_lock = [project.environments[args.environment]]
    else:
        to_lock = project.environments.values()

    for env in to_lock:
        env.lock(force=args.force, verbose=True)

    return True


@handle_errors
def check(args: Namespace) -> bool:
    project = CondaProject(args.directory)
    return project.check(verbose=True)


@handle_errors
def prepare(args: Namespace) -> bool:
    project = CondaProject(args.directory)

    if args.all:
        for _, env in project.environments:
            env.prepare(force=args.force, verbose=True)
    else:
        env = (
            project.environments[args.environment]
            if args.environment
            else project.default_environment
        )
        env.prepare(force=args.force, verbose=True)

    return True


@handle_errors
def clean(args: Namespace) -> bool:
    project = CondaProject(args.directory)

    if args.all:
        for env in project.environments.values():
            env.clean(verbose=True)
    else:
        env = (
            project.environments[args.environment]
            if args.environment
            else project.default_environment
        )
        env.clean(verbose=True)

    return True


@handle_errors
def run(args: Namespace) -> None:
    project = CondaProject(args.directory)

    if args.command:
        to_run = project.commands[args.command]
    else:
        to_run = project.default_command

    to_run.run(environment=args.environment, extra_args=args.extra_args, verbose=True)


@handle_errors
def activate(args: Namespace) -> bool:
    project = CondaProject(args.directory)

    if args.environment:
        env = project.environments[args.environment]
    else:
        env = project.default_environment

    env.activate(project.directory, project._project_file.variables, verbose=True)

    return True
