# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, OrderedDict, TextIO, Union

from pydantic import BaseModel, ValidationError, validator
from ruamel.yaml import YAML

yaml = YAML(typ="rt")
yaml.default_flow_style = False
yaml.block_seq_indent = 2
yaml.indent = 2


def _transform_variables(ap_vars):
    return {
        k: v.get("default") if isinstance(v, dict) else v for k, v in ap_vars.items()
    }


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
            raise ValueError(msg)
        try:
            return cls(**d)
        except ValidationError as e:
            msg = f"Failed to read {fn} as {cls.__name__}\n{str(e)}"
            raise ValueError(msg)

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


class EnvironmentYaml(BaseYaml):
    name: Optional[str] = None
    channels: Optional[List[str]] = None
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


class EnvSpec(BaseModel):
    packages: Optional[List[Union[str, Dict[str, List[str]]]]] = None
    # dependencies: List[Union[str, Dict[str, List[str]]]] = []
    platforms: Optional[List[str]] = None
    channels: Optional[List[str]] = None

    @validator("packages")
    def only_pip_key_allowed(cls, v):
        for item in v:
            if isinstance(item, dict):
                if not item.keys() == {"pip"}:
                    raise ValueError(
                        f'The dependencies key contains an invalid map {item}. Only "pip:" is allowed.'
                    )
        return v


class APCommand(BaseModel):
    unix: Optional[str] = None
    win: Optional[str] = None
    notebook: Optional[str] = None
    bokeh_app: Optional[str] = None
    supports_http_options: Optional[bool] = None
    env_spec: Optional[str] = "default"
    description: Optional[str] = None
    variables: Optional[Dict[str, Optional[Union[str, Dict]]]] = None


class AnacondaProjectYaml(BaseYaml, EnvSpec):
    name: str
    env_specs: Optional[Dict[str, EnvSpec]] = {"default": EnvSpec()}
    commands: Optional[Dict[str, APCommand]] = None
    variables: Optional[Dict[str, Optional[Union[str, Dict]]]] = None
    downloads: Optional[Dict[str, str]] = None
    services: Optional[Dict[str, Any]] = None
    maintainers: Optional[List[str]] = None


if __name__ == "__main__":
    ap_yaml = Path(sys.argv[1])
    if len(sys.argv) == 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = Path(".")

    anaconda_project = AnacondaProjectYaml.parse_yaml(ap_yaml)

    if anaconda_project.packages is not None:
        env = EnvironmentYaml(
            channels=anaconda_project.channels,
            dependencies=anaconda_project.packages,
            platforms=anaconda_project.platforms,
        )
        env_yaml = output_path / "environment.yml"
        with env_yaml.open("wt") as f:
            env.yaml(f, drop_empty_keys=True)

    environments = {}
    for env, spec in anaconda_project.env_specs.items():
        environments[env] = ["environment.yml"]

        if spec.packages is not None:
            local_env = EnvironmentYaml(
                channels=spec.channels,
                platforms=spec.platforms,
                dependencies=spec.packages,
            )
            local_env_yaml = output_path / f"env.{env}.yml"
            with local_env_yaml.open("wt") as f:
                local_env.yaml(f, drop_empty_keys=True)

            environments[env].append(local_env_yaml.relative_to(output_path))

    vars = {}
    if anaconda_project.variables is not None:
        vars = _transform_variables(anaconda_project.variables)

    cmds = {}
    if anaconda_project.commands is not None:
        for cmd, spec in anaconda_project.commands.items():
            this = {}

            if spec.notebook is not None:
                this["cmd"] = f"jupyter notebook {spec.notebook}"
            elif spec.bokeh_app is not None:
                this["cmd"] = f"bokeh serve {spec.bokeh_app}"
            elif spec.unix or spec.win:
                this["cmd"] = spec.unix or spec.win

            this["environment"] = spec.env_spec
            if spec.variables is not None:
                this["variables"] = _transform_variables(spec.variables)

            cmds[cmd] = this

    conda_project = CondaProjectYaml(
        name=anaconda_project.name,
        environments=environments,
        variables=vars,
        commands=cmds,
    )

    conda_project_yaml = output_path / "conda-project.yml"
    with conda_project_yaml.open("wt") as f:
        conda_project.yaml(f, drop_empty_keys=False)
