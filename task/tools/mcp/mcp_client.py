from typing import Optional, Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, TextContent, ReadResourceResult, TextResourceContents, BlobResourceContents
from pydantic import AnyUrl

from task.tools.mcp.mcp_tool_model import MCPToolModel


class MCPClient:
    """Handles MCP server connection and tool execution"""

    def __init__(self, mcp_server_url: str) -> None:
        self.server_url = mcp_server_url
        self.session: Optional[ClientSession] = None
        self._streams_context = None
        self._session_context = None

    @classmethod
    async def create(cls, mcp_server_url: str) -> 'MCPClient':
        """Async factory method to create and connect MCPClient"""
        instance = cls(mcp_server_url)
        await instance.connect()
        return instance

    async def connect(self):
        """Connect to MCP server"""
        if self.session is not None:
            return
        try:
            self._streams_context = streamablehttp_client(self.server_url)
            read_stream, write_stream, _ = await self._streams_context.__aenter__()

            self._session_context = ClientSession(read_stream, write_stream)
            self.session = await self._session_context.__aenter__()

            await self.session.initialize()
            await self.session.send_ping()
        except BaseException as e:
            # Cleanup in the same task where contexts were entered.
            try:
                if self._session_context is not None:
                    await self._session_context.__aexit__(None, None, None)
            except Exception:
                pass
            try:
                if self._streams_context is not None:
                    await self._streams_context.__aexit__(None, None, None)
            except Exception:
                pass
            self.session = None
            self._session_context = None
            self._streams_context = None
            raise ValueError(f"MCP server connection failed ({self.server_url}): {e}")


    async def get_tools(self) -> list[MCPToolModel]:
        """Get available tools from MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")

        tools = await self.session.list_tools()
        return [
            MCPToolModel(
                name=tool.name,
                description=tool.description,
                parameters=tool.inputSchema,
            )
            for tool in tools.tools
        ]

    async def call_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        """Call a tool on the MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")

        tool_result: CallToolResult = await self.session.call_tool(tool_name, tool_args)

        if not tool_result.content:
            return None

        content = tool_result.content[0]

        if isinstance(content, TextContent):
            return content.text

        return content

    async def get_resource(self, uri: AnyUrl) -> str | bytes:
        """Get specific resource content"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")

        resource_result: ReadResourceResult = await self.session.read_resource(uri)

        if not resource_result.contents:
            raise ValueError(f"No content in resource: {uri}")

        content = resource_result.contents[0]

        if isinstance(content, TextResourceContents):
            return content.text
        elif isinstance(content, BlobResourceContents):
            return content.blob
        else:
            raise ValueError(f"Unexpected content type: {type(content)}")

    async def close(self):
        """Close connection to MCP server"""
        try:
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
        except Exception as e:
            print(f"Warning: Error closing session context: {e}")

        try:
            if self._streams_context:
                await self._streams_context.__aexit__(None, None, None)
        except Exception as e:
            print(f"Warning: Error closing streams context: {e}")
        finally:
            self.session = None
            self._session_context = None
            self._streams_context = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
        return False

