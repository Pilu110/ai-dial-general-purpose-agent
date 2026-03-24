import os
import asyncio
from urllib.parse import urlparse

import uvicorn
from aidial_sdk import DIALApp
from aidial_sdk.chat_completion import ChatCompletion, Request, Response

from task.agent import GeneralPurposeAgent
from task.prompts import SYSTEM_PROMPT
from task.tools.base import BaseTool
from task.tools.deployment.image_generation_tool import ImageGenerationTool
from task.tools.files.file_content_extraction_tool import FileContentExtractionTool
from task.tools.py_interpreter.python_code_interpreter_tool import PythonCodeInterpreterTool
from task.tools.mcp.mcp_client import MCPClient
from task.tools.mcp.mcp_tool import MCPTool
from task.tools.rag.document_cache import DocumentCache
from task.tools.rag.rag_tool import RagTool

DIAL_ENDPOINT = os.getenv('DIAL_ENDPOINT', "http://localhost:8080")
DEPLOYMENT_NAME = os.getenv('DEPLOYMENT_NAME', 'gpt-4o')
# DEPLOYMENT_NAME = os.getenv('DEPLOYMENT_NAME', 'claude-haiku-4-5')


class GeneralPurposeAgentApplication(ChatCompletion):

    def __init__(self):
        self.tools: list[BaseTool] = []

    async def _is_mcp_endpoint_reachable(self, url: str, timeout_seconds: float = 1.0) -> bool:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            return False

        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme == "https" else 80

        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout_seconds)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def _get_mcp_tools(self, url: str) -> list[BaseTool]:
        if not await self._is_mcp_endpoint_reachable(url):
            print(f"Warning: MCP endpoint is not reachable, skipping tools: {url}")
            return []

        try:
            tools: list[BaseTool] = []
            mcp_client = await MCPClient.create(url)
            for mcp_tool_model in await mcp_client.get_tools():
                tools.append(
                    MCPTool(
                        client=mcp_client,
                        mcp_tool_model=mcp_tool_model,
                    )
                )
            return tools
        except asyncio.CancelledError as e:
            print(f"Warning: MCP tools initialization cancelled for {url}: {e}")
            return []
        except Exception as e:
            print(f"Warning: Could not load MCP tools from {url}: {e}")
            return []

    async def _create_tools(self) -> list[BaseTool]:
        py_interpreter_mcp_url = os.getenv('PYINTERPRETER_MCP_URL', "http://localhost:8050/mcp")
        print(f"PYINTERPRETER_MCP_URL {py_interpreter_mcp_url}")

        tools: list[BaseTool] = [
            ImageGenerationTool(endpoint=DIAL_ENDPOINT),
            FileContentExtractionTool(endpoint=DIAL_ENDPOINT),
            RagTool(
                endpoint=DIAL_ENDPOINT,
                deployment_name=DEPLOYMENT_NAME,
                document_cache=DocumentCache.create()
            ),
        ]

        if await self._is_mcp_endpoint_reachable(py_interpreter_mcp_url):
            try:
                tools.append(
                    await PythonCodeInterpreterTool.create(
                        mcp_url=py_interpreter_mcp_url,
                        tool_name="execute_code",
                        dial_endpoint=DIAL_ENDPOINT
                    )
                )
            except asyncio.CancelledError as e:
                print(f"Warning: Python interpreter MCP initialization cancelled ({py_interpreter_mcp_url}): {e}")
            except Exception as e:
                print(f"Warning: Python interpreter MCP is unavailable ({py_interpreter_mcp_url}): {e}")
        else:
            print(f"Warning: Python interpreter MCP endpoint is not reachable, skipping: {py_interpreter_mcp_url}")

        ddg_mcp_url = os.getenv('DDG_MCP_URL', "http://localhost:8051/mcp")
        print(f"DDG_MCP_URL {ddg_mcp_url}")
        tools.extend(await self._get_mcp_tools(ddg_mcp_url))

        return tools

    async def chat_completion(self, request: Request, response: Response) -> None:
        if not self.tools:
            self.tools = await self._create_tools()

        with response.create_single_choice() as choice:
            await GeneralPurposeAgent(
                endpoint=DIAL_ENDPOINT,
                system_prompt=SYSTEM_PROMPT,
                tools=self.tools
            ).handle_request(
                choice=choice,
                deployment_name=DEPLOYMENT_NAME,
                request=request,
                response=response,
            )

app: DIALApp = DIALApp()
agent_app = GeneralPurposeAgentApplication()
app.add_chat_completion(deployment_name="general-purpose-agent", impl=agent_app)

# Run the application
if __name__ == "__main__":
    uvicorn.run(app, port=5030, host="0.0.0.0")
