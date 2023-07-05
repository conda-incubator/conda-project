# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Dict, List, Optional, OrderedDict, TextIO, Union

from conda_lock._vendor.conda.models.match_spec import MatchSpec
from pydantic import BaseModel, ValidationError, validator
from ruamel.yaml import YAML

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


def replace_duplicate_matchspec_name(dependencies, to_update):
    names = [MatchSpec(d).name for d in dependencies if not isinstance(d, dict)]
    for dep in to_update:
        m = MatchSpec(dep)
        if m.name in names:
            idx = names.index(m.name)
            dependencies[idx] = dep


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

    @property
    def matchspecs(self):
        return [
            MatchSpec(dep) for dep in self.dependencies if not isinstance(dep, dict)
        ]

    def add_dependencies(
        self,
        dependencies: List[str],
        channels: Optional[Union[UniqueOrderedList, List[str]]] = None,
    ) -> None:
        current_names = [dep.name for dep in self.matchspecs]

        to_add = []
        for dep in dependencies:
            name = MatchSpec(dep).name
            if name in current_names:
                self.dependencies[current_names.index(name)] = dep
            else:
                to_add.append(dep)

        self.dependencies.extend(to_add)

        if channels:
            if self.channels:
                self.channels.extend(channels)
            else:
                self.channels = UniqueOrderedList(channels)

    def remove_dependencies(self, dependencies: List[str]) -> None:
        current_names = [dep.name for dep in self.matchspecs]

        for dep in dependencies:
            name = MatchSpec(dep).name
            if name in current_names:
                self.dependencies.pop(current_names.index(name))
                current_names.remove(name)
