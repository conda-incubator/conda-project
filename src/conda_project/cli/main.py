# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import typing
from argparse import REMAINDER, ArgumentParser

from conda_project import __version__

from ..project import DEFAULT_PLATFORMS
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
        description="Tool for encapsulating, running, and reproducing projects with conda environments",
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

    _create_init_parser(subparsers, common)
    _create_lock_parser(subparsers, common)
    _create_check_parser(subparsers, common)
    _create_install_parser(subparsers, common)
    _create_activate_parser(subparsers, common)
    _create_clean_parser(subparsers, common)
    _create_run_parser(subparsers, common)

    return p


def _create_init_parser(
    subparsers: "_SubParsersAction", parent_parser: ArgumentParser
) -> None:
    """Add a subparser for the "init" and "create" subcommands.

    Args:
        subparsers: The existing subparsers corresponding to the "command" meta-variable.
        parent_parser: The parent parser, which is used to pass common arguments into the subcommands.

    """
    desc = "Initialize a new project"

    # TODO: If we deprecate "create", this loop can go away.
    for subcommand_name in ["init", "create"]:
        p = subparsers.add_parser(
            subcommand_name, description=desc, help=desc, parents=[parent_parser]
        )
        p.add_argument(
            "-n", "--name", help="Name for the project.", action="store", default=None
        )
        p.add_argument(
            "-c",
            "--channel",
            help=(
                "Additional channel to search for packages. The default channel is 'defaults'. "
                "Multiple channels are added with repeated use of this argument."
            ),
            action="append",
        )
        p.add_argument(
            "--platforms",
            help=(
                f"Comma separated list of platforms for which to lock dependencies. "
                f"The default is {','.join(DEFAULT_PLATFORMS)}"
            ),
            action="store",
            default=",".join(DEFAULT_PLATFORMS),
        )
        p.add_argument(
            "--conda-configs",
            help=(
                "Comma separated list of conda configuration parameters to write into the "
                ".condarc file in the project directory. The format for each config is key=value. "
                "For example --conda-configs experimental_solver=libmamba,channel_priority=strict"
            ),
            action="store",
            default=None,
        )
        p.add_argument(
            "--no-lock",
            help="Do not create the conda-lock.<env>.yml file(s)",
            action="store_true",
        )
        p.add_argument(
            "--install",
            help="Create the local conda environment for the current platform.",
            action="store_true",
        )
        p.add_argument(
            "dependencies",
            help=(
                "Packages to add to the environment.yml. The format for each package is '<name>[<op><version>]' "
                "where <op> can be =, <, >, <=, or >=."
            ),
            action="store",
            nargs="*",
            metavar="PACKAGE_SPECIFICATION",
        )

        p.set_defaults(func=getattr(commands, subcommand_name))


def _create_lock_parser(
    subparsers: "_SubParsersAction", parent_parser: ArgumentParser
) -> None:
    """Add a subparser for the "lock" subcommand.

    Args:
        subparsers: The existing subparsers corresponding to the "command" meta-variable.
        parent_parser: The parent parser, which is used to pass common arguments into the subcommands.

    """
    desc = "Lock all conda environments or a specific one by creating conda-lock.<env>.yml file(s)."

    p = subparsers.add_parser(
        "lock", description=desc, help=desc, parents=[parent_parser]
    )
    p.add_argument(
        "environment",
        help="Optional: Lock the selected environment. If no environment name is selected "
        "all environments are locked.",
        nargs="?",
    )
    p.add_argument(
        "--force",
        help="Remove and recreate existing conda-lock.<env>.yml file(s).",
        action="store_true",
    )

    p.set_defaults(func=commands.lock)


def _create_check_parser(
    subparsers: "_SubParsersAction", parent_parser: ArgumentParser
) -> None:
    """Add a subparser for the "lock" subcommand.

    Args:
        subparsers: The existing subparsers corresponding to the "command" meta-variable.
        parent_parser: The parent parser, which is used to pass common arguments into the subcommands.

    """
    desc = (
        "Check the project for inconsistencies or errors. This will check that conda-lock.<env>.yml file(s) "
        "have been created for each environment and are up-to-date with the source environment specifications. "
        "If the project is fully locked this command will not print anything and return status code 0. If any "
        "environment is not fully locked details are printed to stderr and the command returns status code 1."
    )

    p = subparsers.add_parser(
        "check", description=desc, help=desc, parents=[parent_parser]
    )

    p.set_defaults(func=commands.check)


def _create_install_parser(
    subparsers: "_SubParsersAction", parent_parser: ArgumentParser
) -> None:
    """Add a subparser for the "install" and "prepare" subcommands.

    Args:
        subparsers: The existing subparsers corresponding to the "command" meta-variable.
        parent_parser: The parent parser, which is used to pass common arguments into the subcommands.

    """
    desc = "Install the packages into the conda environments"

    for subcommand_name in ["install", "prepare"]:
        p = subparsers.add_parser(
            subcommand_name, description=desc, help=desc, parents=[parent_parser]
        )
        group = p.add_mutually_exclusive_group(required=False)
        group.add_argument(
            "environment",
            help="Prepare the selected environment. If no environment name is selected "
            "the first environment defined in the conda-project.yml file is prepared.",
            nargs="?",
        )
        group.add_argument(
            "--as-platform",
            help="Prepare the conda environment assuming a different platform/subdir name.",
            action="store",
            metavar="PLATFORM",
        )
        group.add_argument(
            "--all",
            help="Check or prepare all defined environments.",
            action="store_true",
        )
        p.add_argument(
            "--check-only",
            help="Check that the prepared conda environment exists and is up-to-date with the "
            "source environment and files and lockfile and then exit. If the environment is up-to-date "
            "nothing is printed and the command exists with 0. If the environment is missing or out-of-date "
            "details are printed to stderr and the command exits with 1.",
            action="store_true",
        )
        p.add_argument(
            "--force",
            help="Remove and recreate an existing environment.",
            action="store_true",
        )

        p.set_defaults(func=getattr(commands, subcommand_name))


def _create_clean_parser(
    subparsers: "_SubParsersAction", parent_parser: ArgumentParser
) -> None:
    """Add a subparser for the "clean" subcommand.

    Args:
        subparsers: The existing subparsers corresponding to the "command" meta-variable.
        parent_parser: The parent parser, which is used to pass common arguments into the subcommands.

    """
    desc = "Clean the conda environments"

    p = subparsers.add_parser(
        "clean", description=desc, help=desc, parents=[parent_parser]
    )
    p.add_argument(
        "environment",
        help="Remove environment prefix for selected environment. If no environment name is selected "
        "the first environment defined in the conda-project.yml file is removed.",
        nargs="?",
    )
    p.add_argument(
        "--all", help="Prepare all defined environments.", action="store_true"
    )

    p.set_defaults(func=commands.clean)


def _create_run_parser(
    subparsers: "_SubParsersAction", parent_parser: ArgumentParser
) -> None:
    """Add a subparser for the "run" subcommand.

    Args:
        subparsers: The existing subparsers corresponding to the "command" meta-variable.
        parent_parser: The parent parser, which is used to pass common arguments into the subcommands.

    """
    desc = "Run commands in project environments."

    p = subparsers.add_parser(
        "run", description=desc, help=desc, parents=[parent_parser]
    )
    p.add_argument(
        "--environment",
        help=(
            "Specify the environment in which to run the command. The default environment for the command is either "
            "what was specified in the command definition or the first environment defined in the project."
        ),
    )
    p.add_argument(
        "command",
        help="Optional: Run a command in the conda environment. The full command can be provided on the CLI "
        "or the name of a command defined in the conda-project.yml file. If no command is provided "
        "the first command in the conda-project.yml file is run if there is one.",
        nargs="?",
    )
    p.add_argument(
        "extra_args",
        help="Optional arguments passed to the command",
        nargs=REMAINDER,
        default=None,
    )

    p.set_defaults(func=commands.run)


def _create_activate_parser(
    subparsers: "_SubParsersAction", parent_parser: ArgumentParser
) -> None:
    """Add a subparser for the "run" subcommand.

    Args:
        subparsers: The existing subparsers corresponding to the "command" meta-variable.
        parent_parser: The parent parser, which is used to pass common arguments into the subcommands.

    """
    desc = "Activate a conda environment defined in the environment.yml or conda-project.yml files."

    p = subparsers.add_parser(
        "activate", description=desc, help=desc, parents=[parent_parser]
    )
    p.add_argument(
        "environment",
        help="Activate selected environment in a new shell. If no environment name is selected "
        "the first environment defined in the conda-project.yml file is activated.",
        nargs="?",
    )

    p.set_defaults(func=commands.activate)


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
