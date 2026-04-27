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

# Required environment variables:
#   SPANNER_PROJECT   — GCP project ID
#   SPANNER_INSTANCE  — Spanner instance ID
#   SPANNER_DATABASE  — Spanner database ID

import os

import google.auth
import google.auth.transport.requests
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools import FunctionalToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

SPANNER_SCOPE = 'https://www.googleapis.com/auth/spanner.data'
SPANNER_MCP_ENDPOINT = 'https://spanner.googleapis.com/mcp'

credentials, _ = google.auth.default(scopes=[SPANNER_SCOPE])
credentials.refresh(google.auth.transport.requests.Request())

spanner_mcp = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=SPANNER_MCP_ENDPOINT,
        headers={'Authorization': f'Bearer {credentials.token}'},
    )
)

tools = FunctionalToolset(
    os.path.join(os.path.dirname(__file__), 'tools.yaml'),
    spanner_mcp,
    toolset_name='order_management',
)

root_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='order_management_agent',
    description='Agent to look up users and orders using Spanner.',
    instruction="""\
        You are an order management assistant with read-only access to Spanner.

        Before running any query you MUST call create_session to obtain a session
        name. Pass that session name to every subsequent query tool call.

        Use the available tools to look up users and list orders by status.
    """,
    tools=[tools],
)
