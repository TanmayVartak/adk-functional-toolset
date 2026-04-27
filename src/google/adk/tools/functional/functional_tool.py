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

from typing import Any

from google.genai import types

from ..base_tool import BaseTool
from ..tool_context import ToolContext
from .yaml_config import InputParam
from .yaml_config import ToolDefinition

_YAML_TO_JSON_SCHEMA = {
    'string': 'string',
    'integer': 'integer',
    'float': 'number',
    'boolean': 'boolean',
}


def _substitute(template: Any, resolved: dict[str, Any]) -> Any:
  if isinstance(template, str):
    for name, val in resolved.items():
      template = template.replace(
          f'${{{name}}}', str(val) if val is not None else ''
      )
    return template
  if isinstance(template, dict):
    return {k: _substitute(v, resolved) for k, v in template.items()}
  return template


class FunctionalTool(BaseTool):
  """A tool whose schema and input mapping are defined in a YAML config."""

  def __init__(self, tool_def: ToolDefinition, mapped_tool: BaseTool):
    super().__init__(name=tool_def.name, description=tool_def.description)
    self._tool_def = tool_def
    self._mapped_tool = mapped_tool

  def _get_declaration(self) -> types.FunctionDeclaration:
    properties: dict[str, Any] = {}
    required_fields: list[str] = []
    for param in self._all_params():
      schema: dict[str, Any] = {
          'type': _YAML_TO_JSON_SCHEMA.get(param.type, 'string'),
          'description': param.description,
      }
      if param.default is not None:
        schema['default'] = param.default
      properties[param.name] = schema
      if param.required:
        required_fields.append(param.name)
    return types.FunctionDeclaration(
        name=self._tool_def.name,
        description=self._tool_def.description,
        parameters={
            'type': 'object',
            'properties': properties,
            'required': required_fields,
        },
    )

  async def run_async(
      self, *, args: dict[str, Any], tool_context: ToolContext
  ) -> Any:
    resolved = {
        p.name: args.get(p.name, p.default) for p in self._all_params()
    }
    base_args: dict[str, Any] = {}
    for key, value in self._tool_def.inputs.items():
      if isinstance(value, list):
        base_args[key] = [_substitute(p.mapped_value, resolved) for p in value]
      elif isinstance(value, InputParam):
        if value.mapped_value is not None:
          base_args[key] = _substitute(value.mapped_value, resolved)
        else:
          base_args[key] = resolved.get(value.name)
      else:
        base_args[key] = value
    return await self._mapped_tool.run_async(
        args=base_args, tool_context=tool_context
    )

  def _all_params(self) -> list[InputParam]:
    params: list[InputParam] = []
    for value in self._tool_def.inputs.values():
      if isinstance(value, list):
        params.extend(value)
      elif isinstance(value, InputParam):
        params.append(value)
    return params
