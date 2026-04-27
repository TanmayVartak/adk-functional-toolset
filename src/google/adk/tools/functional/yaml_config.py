# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Optional

import yaml


@dataclass
class InputParam:
  name: str
  type: str
  description: str
  required: bool = True
  default: Any = None
  mapped_value: Any = None


@dataclass
class ToolDefinition:
  name: str
  source: str
  mapped_tool: str
  description: str
  inputs: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolsetDefinition:
  name: str
  tools: list[str]


@dataclass
class YamlConfig:
  sources: set[str]
  tools: dict[str, ToolDefinition]
  toolsets: dict[str, ToolsetDefinition]


_ENV_VAR_RE = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)(?::([^}]*))?\}')


def _substitute_env(text: str) -> str:
  def replace(m: re.Match) -> str:
    var_name, default = m.group(1), m.group(2)
    value = os.environ.get(var_name)
    if value is not None:
      return value
    if default is not None:
      return default
    return m.group(0)

  return _ENV_VAR_RE.sub(replace, text)


def _substitute_env_deep(obj: Any) -> Any:
  if isinstance(obj, str):
    return _substitute_env(obj)
  if isinstance(obj, dict):
    return {k: _substitute_env_deep(v) for k, v in obj.items()}
  if isinstance(obj, list):
    return [_substitute_env_deep(i) for i in obj]
  return obj


def _parse_input_param(name: str, raw: dict) -> InputParam:
  return InputParam(
      name=raw.get('name', name),
      type=raw.get('type', 'string'),
      description=raw.get('description', ''),
      required=raw.get('required', True),
      default=raw.get('default'),
      mapped_value=raw.get('mapped_value'),
  )


def _parse_inputs(raw_inputs: dict) -> dict[str, Any]:
  result = {}
  for key, value in raw_inputs.items():
    if isinstance(value, list):
      result[key] = [
          _parse_input_param(item.get('name', key), item) for item in value
      ]
    elif isinstance(value, dict) and 'type' in value:
      result[key] = _parse_input_param(key, value)
    else:
      result[key] = value
  return result


def _parse_tool(raw: dict) -> ToolDefinition:
  return ToolDefinition(
      name=raw['name'],
      source=raw['source'],
      mapped_tool=raw['mapped_tool'],
      description=raw.get('description', ''),
      inputs=_parse_inputs(raw.get('inputs', {})),
  )


def load_yaml_config(yaml_path: str) -> YamlConfig:
  with open(yaml_path, 'r') as f:
    content = f.read()

  content = _substitute_env(content)
  raw = yaml.safe_load(content)

  sources: set[str] = set()
  tools: dict[str, ToolDefinition] = {}
  toolsets: dict[str, ToolsetDefinition] = {}

  docs = raw if isinstance(raw, list) else [raw]

  for doc in docs:
    if not isinstance(doc, dict):
      continue
    kind = doc.get('kind')

    if kind == 'source':
      sources.add(doc['name'])

    elif kind == 'tool':
      doc = _substitute_env_deep(doc)
      tool = _parse_tool(doc)
      tools[tool.name] = tool

    elif kind == 'toolset':
      toolsets[doc['name']] = ToolsetDefinition(
          name=doc['name'],
          tools=doc.get('tools', []),
      )

    elif isinstance(doc, dict):
      for sub_key in ('sources', 'tools', 'toolsets'):
        for item in doc.get(sub_key, []):
          item = _substitute_env_deep(item)
          if sub_key == 'sources':
            sources.add(item['name'])
          elif sub_key == 'tools':
            tool = _parse_tool(item)
            tools[tool.name] = tool
          elif sub_key == 'toolsets':
            toolsets[item['name']] = ToolsetDefinition(
                name=item['name'],
                tools=item.get('tools', []),
            )

  return YamlConfig(sources=sources, tools=tools, toolsets=toolsets)
