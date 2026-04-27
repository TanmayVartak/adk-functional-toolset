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

import os
from typing import Optional

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import FunctionalToolset
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.function_tool import FunctionTool

_GREETINGS = {
    'english': 'Hello',
    'spanish': 'Hola',
    'french': 'Bonjour',
    'german': 'Hallo',
    'japanese': 'Konnichiwa',
}


def greet(user_name: str, language: str = 'english') -> str:
  """Return a greeting for the user in the requested language."""
  word = _GREETINGS.get(language.lower(), 'Hello')
  return f'{word}, {user_name}!'


class _FunctionListToolset(BaseToolset):
  """Minimal toolset that wraps a fixed list of BaseTool instances."""

  def __init__(self, *tools: BaseTool):
    super().__init__()
    self._tools = list(tools)

  async def get_tools(
      self, readonly_context: Optional[ReadonlyContext] = None
  ) -> list[BaseTool]:
    return self._tools

  async def close(self) -> None:
    pass


greet_toolset = _FunctionListToolset(FunctionTool(greet))

tools = FunctionalToolset(
    os.path.join(os.path.dirname(__file__), 'tools.yaml'),
    greet_toolset,
    toolset_name='greet_toolset',
)

root_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='greet_agent',
    description='Agent that greets users in different languages.',
    instruction='You are a greeting assistant. Use the greet_user tool to greet users.',
    tools=[tools],
)
