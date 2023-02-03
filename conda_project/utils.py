# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import itertools
import os
import platform
import sys
import threading
import time
from collections import ChainMap
from collections.abc import Generator
from contextlib import contextmanager
from inspect import Traceback
from pathlib import Path
from subprocess import Popen
from typing import Dict, List, NoReturn, Optional, Type, Union

from dotenv import dotenv_values

from .exceptions import CondaProjectError


@contextmanager
def env_variable(key: str, value: str) -> Generator:
    """Temporarily set environment variable in a context manager."""
    old = os.environ.get(key, None)
    os.environ[key] = value

    yield

    if old is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = old


class Spinner:
    """Multithreaded CLI spinner context manager

    Attributes:
        prefix: Text to display at the start of the line

    Args:
        prefix: Text to display at the start of the line

    """

    def __init__(self, prefix: str):
        self.prefix = prefix
        self._event = threading.Event()
        self._thread = threading.Thread(target=self._spin)

    def _spin(self) -> None:
        spinner = itertools.cycle(["◜", "◠", "◝", "◞", "◡", "◟"])

        while not self._event.is_set():
            sys.stdout.write("\r")
            sys.stdout.write("\033[K")
            sys.stdout.write(f"{self.prefix}: {next(spinner)} ")
            sys.stdout.flush()
            time.sleep(0.10)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._event.set()
        self._thread.join()
        sys.stdout.write("\r")
        sys.stdout.write("\033[K")
        sys.stdout.write(f"{self.prefix}: done\n")
        sys.stdout.flush()

    def __enter__(self) -> None:
        self.start()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        exc_tb: Optional[Traceback],
    ) -> None:
        self.stop()


def find_file(directory: Path, options: tuple) -> Optional[Path]:
    """Search for a file in a directory from a tuple of variants.

    Returns:
        The path to the file if found else None

    Raises:
        CondaProjectError if more than one of the options is found

    """
    found = []

    for filename in options:
        path = directory / filename
        if path.exists():
            found.append(path.resolve())

    if len(found) == 1:
        return found[0]
    elif len(found) > 1:
        _found_files = "\n".join([str(p) for p in found])
        raise CondaProjectError(
            f"Multiple variants of the same file were found.\n{_found_files}\nConsider using one of them."
        )
    else:
        return None


def merge_dicts(*dicts):
    return dict(ChainMap(*reversed(dicts)))


def prepare_variables(project_directory: Path, *variable_dicts) -> Dict[str, str]:
    variables = [{} if vars is None else vars for vars in variable_dicts]

    dotenv = dotenv_values(project_directory / ".env")

    env = merge_dicts(*variables, dotenv, os.environ)

    missing_vars = [k for k, v in env.items() if v is None]
    if missing_vars:
        errs = "\n".join(missing_vars)
        msg = (
            "The following variables do not have a default value and values\n"
            "were not provided in the .env file or set on the command line"
            f" when executing 'conda project run':\n{errs}"
        )
        raise CondaProjectError(msg)

    return env


def is_windows():
    return platform.system() == "Windows"


def execvped(
    file: Union[Path, str], args: List[str], env: Dict[str, str], cwd: Union[Path, str]
) -> NoReturn:
    """A cross-platform os.execvpe - like executor

    The goal is the be able to launch a command in a working directory,
    with environment variables and exit to the shell with the return code
    of the command and ensure that on error the previous working directory
    is restored.

    The "d" in the function name refers to the requirement that
    the working directory (cwd) flag be used.
    """

    sys.stdout.flush()
    sys.stderr.flush()

    if is_windows():
        sys.exit(Popen(args=[file, *args], env=env, cwd=cwd).wait())
    else:
        old_dir = Path.cwd()
        try:
            os.chdir(cwd)
            os.execvpe(file, args, env)
        finally:
            os.chdir(old_dir)
