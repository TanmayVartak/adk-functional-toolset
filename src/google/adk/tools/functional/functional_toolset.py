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

from typing import Optional
from typing import Union

from google.adk.agents.readonly_context import ReadonlyContext

from ..base_tool import BaseTool
from ..base_toolset import BaseToolset
from ..base_toolset import ToolPredicate
from .functional_tool import FunctionalTool
from .yaml_config import load_yaml_config
from .yaml_config import ToolDefinition
from .yaml_config import YamlConfig


class FunctionalToolset(BaseToolset):
  """A toolset that maps YAML tool definitions to a base toolset's tools.

  Each tool defined in the YAML file is backed by a named tool from the
  provided base toolset. The YAML inputs section with optional mapped_value
  templates defines how LLM-provided arguments are transformed into the base
  tool's expected arguments.
  """

  def __init__(
      self,
      yaml_path: str,
      base_toolset: Union[BaseToolset, dict[str, BaseToolset]],
      *,
      toolset_name: Optional[str] = None,
      tool_filter: Optional[Union[ToolPredicate, list[str]]] = None,
      tool_name_prefix: Optional[str] = None,
  ):
    super().__init__(tool_filter=tool_filter, tool_name_prefix=tool_name_prefix)
    self._config: YamlConfig = load_yaml_config(yaml_path)
    self._base_toolset = base_toolset
    self._toolset_name = toolset_name

  def _resolve_base_toolset(self, source_name: str) -> BaseToolset:
    if isinstance(self._base_toolset, dict):
      if source_name not in self._base_toolset:
        raise ValueError(
            f"No base_toolset provided for source '{source_name}'. "
            f'Available: {list(self._base_toolset.keys())}'
        )
      return self._base_toolset[source_name]
    return self._base_toolset

  async def get_tools(
      self,
      readonly_context: Optional[ReadonlyContext] = None,
  ) -> list[BaseTool]:
    result: list[BaseTool] = []
    tool_map_cache: dict[str, dict[str, BaseTool]] = {}

    for tool_def in self._get_active_tool_defs():
      if tool_def.source not in tool_map_cache:
        base = self._resolve_base_toolset(tool_def.source)
        discovered = await base.get_tools(readonly_context)
        tool_map_cache[tool_def.source] = {t.name: t for t in discovered}

      tool_map = tool_map_cache[tool_def.source]
      if tool_def.mapped_tool not in tool_map:
        raise ValueError(
            f"Tool '{tool_def.name}': mapped_tool '{tool_def.mapped_tool}'"
            f' not found in base_toolset for source \'{tool_def.source}\'.'
            f' Available: {sorted(tool_map.keys())}'
        )

      tool = FunctionalTool(tool_def, tool_map[tool_def.mapped_tool])
      if self._is_tool_selected(tool, readonly_context):
        result.append(tool)

    return result

  def _get_active_tool_defs(self) -> list[ToolDefinition]:
    if self._toolset_name:
      ts = self._config.toolsets.get(self._toolset_name)
      if ts is None:
        raise ValueError(
            f"Toolset '{self._toolset_name}' not found in YAML config. "
            f'Available: {list(self._config.toolsets.keys())}'
        )
      return [self._config.tools[n] for n in ts.tools]
    return list(self._config.tools.values())

  async def close(self) -> None:
    if isinstance(self._base_toolset, dict):
      for ts in self._base_toolset.values():
        await ts.close()
    else:
      await self._base_toolset.close()
