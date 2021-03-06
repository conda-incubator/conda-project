# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import typing
from argparse import ArgumentParser

from conda_project import __version__

from . import commands

if typing.TYPE_CHECKING:
    # This is here to prevent potential future breaking API changes
    # in argparse from affecting at runtime
    from argparse import _SubParsersAction


def cli() -> ArgumentParser:
    """Construct the command-line argument parser."""
    common = ArgumentParser(add_help=False)
    common.add_argument(
        "--directory",
        metavar="PROJECT_DIR",
        default=".",
        help="Project directory (defaults to current directory)",
    )

    p = ArgumentParser(
        description="Tool for encapsulating, running, and reproducing projects with Conda environments",
        conflict_handler="resolve",
    )
    p.add_argument(
        "-V",
        "--version",
        action="version",
        help="Show the conda-prefix-replacement version number and exit.",
        version="conda_project %s" % __version__,
    )

    subparsers = p.add_subparsers(metavar="command", required=True)

    _create_prepare_parser(subparsers, common)
    _create_clean_parser(subparsers, common)

    return p


def _create_prepare_parser(
    subparsers: "_SubParsersAction", parent_parser: ArgumentParser
) -> None:
    """Add a subparser for the "prepare" subcommand.

    Args:
        subparsers: The existing subparsers corresponding to the "command" meta-variable.
        parent_parser: The parent parser, which is used to pass common arguments into the subcommands.

    """
    desc = "Prepare the Conda environments"

    p = subparsers.add_parser(
        "prepare", description=desc, help=desc, parents=[parent_parser]
    )
    p.add_argument(
        "--force",
        help="Remove and recreate an existing environment.",
        action="store_true",
    )

    p.set_defaults(func=commands.prepare)


def _create_clean_parser(
    subparsers: "_SubParsersAction", parent_parser: ArgumentParser
) -> None:
    """Add a subparser for the "clean" subcommand.

    Args:
        subparsers: The existing subparsers corresponding to the "command" meta-variable.
        parent_parser: The parent parser, which is used to pass common arguments into the subcommands.

    """
    desc = "Clean the Conda environments"

    p = subparsers.add_parser(
        "clean", description=desc, help=desc, parents=[parent_parser]
    )

    p.set_defaults(func=commands.clean)


def parse_and_run(args: list[str] | None = None) -> int:
    """Parse the command-line arguments and run the appropriate sub-command.

    Args:
        args: Command-line arguments. Defaults to system arguments.

    Returns:
        The return code to pass to the operating system.

    """
    p = cli()
    parsed_args, _ = p.parse_known_args(args)
    return parsed_args.func(parsed_args)


def main() -> int:
    """Main entry-point into the `conda-project` command-line interface."""
    import sys

    if len(sys.argv) == 1:
        args = ["-h"]
    else:
        args = sys.argv[1:]

    retcode = parse_and_run(args)
    return retcode
