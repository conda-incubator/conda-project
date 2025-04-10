# -*- coding: utf-8 -*-
# Copyright (C) 2022-2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import logging
import sys
from argparse import Namespace
from functools import wraps
from typing import Any, Callable, NoReturn

from ..exceptions import CommandNotFoundError, CondaProjectError
from ..project import Command, CondaProject, Environment

logger = logging.getLogger(__name__)


def _load_project(args: Namespace):
    if args.project_archive is not None:
        _storage_options = (
            []
            if args.archive_storage_options is None
            else args.archive_storage_options.split(",")
        )

        storage_options = {}
        for option in _storage_options:
            k, v = option.split("=")
            storage_options[k] = v

        project = CondaProject.from_archive(
            args.project_archive,
            storage_options=storage_options,
            output_directory=args.directory,
        )
    else:
        project = CondaProject(args.directory)

    return project


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
def init(args: Namespace) -> bool:
    project = CondaProject.init(
        directory=args.directory,
        name=args.name,
        dependencies=args.dependencies,
        channels=args.channel,
        platforms=args.platforms.split(","),
        conda_configs=(
            [] if args.conda_configs is None else args.conda_configs.split(",")
        ),
        lock_dependencies=args.lock,
        from_environment=args.from_environment,
        verbose=True,
    )

    if args.install:
        project.default_environment.install(verbose=True)

    return True


def create(args: Namespace) -> int:
    logger.warning(
        "The 'create' subcommand is an alias for 'init' and may be removed in a future version."
    )
    return init(args)


@handle_errors
def lock(args: Namespace) -> bool:
    project = _load_project(args)

    if args.environment:
        to_lock = [project.environments[args.environment]]
    else:
        to_lock = project.environments.values()

    for env in to_lock:
        env.lock(force=args.force, verbose=True)

    return True


@handle_errors
def check(args: Namespace) -> bool:
    project = _load_project(args)
    return project.check(verbose=True)


def _get_environment_from_args(project: CondaProject, args: Namespace) -> Environment:
    if args.for_command:
        env = project.commands[args.for_command].environment
        environment = env.name if env is not None else None
    else:
        environment = args.environment

    env = (
        project.environments[environment]
        if environment
        else project.default_environment
    )
    return env


@handle_errors
def install(args: Namespace) -> bool:
    project = _load_project(args)

    if args.all:
        for _, env in project.environments:
            env.install(force=args.force, verbose=True)
    else:
        if args.environment and args.for_command:
            raise CondaProjectError(
                "You must specify one of environment or --for-command"
            )

        env = _get_environment_from_args(project, args)
        env.install(force=args.force, as_platform=args.as_platform, verbose=True)

    return True


def prepare(args: Namespace) -> int:
    logger.warning(
        "The 'prepare' subcommand is an alias for 'install' and may be removed in a future version."
    )
    return install(args)


@handle_errors
def add(args: Namespace) -> bool:
    project = _load_project(args)

    env = (
        project.environments[args.environment]
        if args.environment
        else project.default_environment
    )

    env.add(args.dependencies, args.channel, verbose=True)
    return True


@handle_errors
def remove(args: Namespace) -> bool:
    project = _load_project(args)

    env = (
        project.environments[args.environment]
        if args.environment
        else project.default_environment
    )

    env.remove(args.dependencies, verbose=True)
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
def run(args: Namespace) -> NoReturn:
    project = _load_project(args)

    if args.command:
        try:
            to_run = project.commands[args.command]
        except CommandNotFoundError:
            to_run = Command(
                name=str(args.command),
                cmd=args.command,
                environment=project.default_environment,
                project=project,
            )
    else:
        to_run = project.default_command

    to_run.run(
        environment=args.environment,
        external_environment=args.external_environment,
        extra_args=args.extra_args,
        verbose=True,
    )


@handle_errors
def activate(args: Namespace) -> bool:
    project = _load_project(args)

    if args.environment:
        env = project.environments[args.environment]
    else:
        env = project.default_environment

    env.activate(verbose=True)

    return True
