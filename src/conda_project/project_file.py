# Copyright (C) 2022-2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Dict, List, Optional, OrderedDict, TextIO, Union

from conda_lock._vendor.conda.models.match_spec import MatchSpec
from pkg_resources import Requirement
from ruamel.yaml import YAML

try:  # pragma: no cover
    # Version 2 provides a v1 API
    from pydantic.v1 import BaseModel, ValidationError, validator  # pragma: no cover
except ImportError:  # pragma: no cover
    from pydantic import BaseModel  # type: ignore; #pragma: no cover
    from pydantic import ValidationError  # type: ignore; #pragma: no cover
    from pydantic import validator  # type: ignore; #pragma: no cover

from .exceptions import CondaProjectError

PROJECT_YAML_FILENAMES = ("conda-project.yml", "conda-project.yaml")
ENVIRONMENT_YAML_FILENAMES = ("environment.yml", "environment.yaml")

yaml = YAML(typ="rt")
yaml.default_flow_style = False
yaml.block_seq_indent = 2
yaml.indent = 2


def _cleandict(d: Dict) -> Dict:
    return {k: v for k, v in d.items() if v is not None}


class BaseYaml(BaseModel):
    def yaml(self, stream: Union[TextIO, Path], drop_empty_keys=False):
        # Passing through self.json() allows json_encoders
        # to serialize objects.
        object_hook = _cleandict if drop_empty_keys else None
        encoded = json.loads(self.json(), object_hook=object_hook)
        return yaml.dump(encoded, stream)

    @classmethod
    def parse_yaml(cls, fn: Union[str, Path]):
        d = yaml.load(fn)
        if d is None:
            msg = (
                f"Failed to read {fn} as {cls.__name__}. The file appears to be empty."
            )
            raise CondaProjectError(msg)
        try:
            return cls(**d)
        except ValidationError as e:
            msg = f"Failed to read {fn} as {cls.__name__}\n{str(e)}"
            raise CondaProjectError(msg)

    class Config:
        json_encoders = {Path: lambda v: v.as_posix()}


class Command(BaseModel):
    cmd: str
    environment: Optional[str] = None
    variables: Optional[Dict[str, Optional[str]]] = None

    class Config:
        extra = "forbid"


class CondaProjectYaml(BaseYaml):
    name: str
    environments: OrderedDict[str, List[Path]]
    variables: Dict[str, Optional[str]] = {}
    commands: OrderedDict[str, Union[Command, str]] = OrderedDict()


class UniqueOrderedList(list):
    def __init__(self, iterable: Iterable):
        uniques = []
        for item in iterable:
            if item not in uniques:
                uniques.append(item)

        super().__init__(uniques)

    def _remove_duplicates(self, other: Any):
        for item in self:
            if item in other:
                other.remove(item)

    def append(self, __object: Any) -> None:
        if __object not in self:
            return super().append(__object)

    def extend(self, __iterable: Iterable) -> None:
        self._remove_duplicates(__iterable)
        return super().extend(__iterable)


class EnvironmentYaml(BaseYaml):
    name: Optional[str] = None
    channels: Optional[Union[UniqueOrderedList, List[str]]] = None
    dependencies: List[Union[str, Dict[str, List[str]]]] = []
    variables: Optional[Dict[str, str]] = None
    prefix: Optional[Path] = None
    platforms: Optional[List[str]] = None

    @validator("dependencies")
    def only_pip_key_allowed(cls, v):
        for item in v:
            if isinstance(item, dict):
                if not item.keys() == {"pip"}:
                    raise ValueError(
                        f'The dependencies key contains an invalid map {item}. Only "pip:" is allowed.'
                    )
        return v

    @validator("channels")
    def convert_channels_list(cls, v):
        if not isinstance(v, UniqueOrderedList):
            return UniqueOrderedList(v)
        else:
            return v

    @property
    def conda_matchspecs(self):
        return [
            MatchSpec(dep) for dep in self.dependencies if not isinstance(dep, dict)
        ]

    @property
    def _pip_requirements(self):
        return [d for d in self.dependencies if isinstance(d, dict) and "pip" in d]

    @property
    def pip_requirements(self):
        pip = self._pip_requirements
        if pip:
            return [Requirement(dep) for dep in self._pip_requirements[0]["pip"]]
        else:
            return []

    def _add_pip_requirements(self, reqs):
        if "pip" not in self.dependencies:
            print(
                "Warning: you have pip-installed dependencies in your environment file, "
                "but you do not list pip itself as one of your conda dependencies. Please "
                "add an explicit pip dependency. I'm adding one for you, but still nagging you."
            )
            self.dependencies.append("pip")
        pip = self._pip_requirements
        if pip:
            pip[0]["pip"].extend(reqs)
        else:
            self.dependencies.append({"pip": reqs})

    def _replace_pip_requirement(self, idx, req):
        pip = self._pip_requirements
        if pip:
            pip[0]["pip"][idx] = req

    def _remove_pip_requirement(self, idx):
        pip = self._pip_requirements
        if pip:
            pip[0]["pip"].pop(idx)

    def add_dependencies(
        self,
        dependencies: List[str],
        channels: Optional[Union[UniqueOrderedList, List[str]]] = None,
    ) -> None:
        current_conda_names = [dep.name for dep in self.conda_matchspecs]
        current_pip_names = [dep.name for dep in self.pip_requirements]

        conda_to_add = []
        pip_to_add = []
        for dep in dependencies:
            if dep.startswith("@pip::"):
                _, dep = dep.split("::", maxsplit=1)
                name = Requirement(dep).name
                if name in current_pip_names:
                    self._replace_pip_requirement(current_pip_names.index(name), dep)
                else:
                    pip_to_add.append(dep)
            else:
                name = MatchSpec(dep).name
                if name in current_conda_names:
                    self.dependencies[current_conda_names.index(name)] = dep
                else:
                    conda_to_add.append(dep)

        self.dependencies.extend(conda_to_add)
        if pip_to_add:
            self._add_pip_requirements(pip_to_add)

        if channels:
            if self.channels:
                self.channels.extend(channels)
            else:
                self.channels = UniqueOrderedList(channels)

    def remove_dependencies(self, dependencies: List[str]) -> None:
        current_conda_names = [dep.name for dep in self.conda_matchspecs]
        current_pip_names = [dep.name for dep in self.pip_requirements]

        for dep in dependencies:
            if dep.startswith("@pip::"):
                _, dep = dep.split("::", maxsplit=1)
                name = Requirement(dep).name
                if name in current_pip_names:
                    self._remove_pip_requirement(current_pip_names.index(name))
            else:
                name = MatchSpec(dep).name
                if name in current_conda_names:
                    self.dependencies.pop(current_conda_names.index(name))
                    current_conda_names.remove(name)
