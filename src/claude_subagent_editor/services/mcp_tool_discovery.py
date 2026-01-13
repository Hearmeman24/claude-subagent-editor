"""MCP tool discovery service for querying tools from MCP servers."""

import asyncio
import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Timeout for MCP server queries (in seconds)
MCP_QUERY_TIMEOUT = 10


@dataclass
class MCPToolInfo:
    """Information about a discovered MCP tool."""

    name: str  # Original tool name from server
    full_name: str  # Full name with server prefix: mcp__server__tool
    description: str | None = None


@dataclass
class MCPServerWithTools:
    """MCP server with its discovered tools."""

    name: str
    connected: bool
    error: str | None = None
    tools: list[MCPToolInfo] | None = None


class MCPToolDiscovery:
    """Service for discovering tools from MCP servers."""

    async def discover_all_tools(self, mcp_config_path: Path) -> list[MCPServerWithTools]:
        """Discover tools from all MCP servers in configuration.

        Args:
            mcp_config_path: Path to .mcp.json file.

        Returns:
            list[MCPServerWithTools]: List of servers with their tools.
        """
        servers: list[MCPServerWithTools] = []

        # Load MCP configuration
        if not mcp_config_path.exists():
            logger.debug("MCP config not found: %s", mcp_config_path)
            return servers

        try:
            config = json.loads(mcp_config_path.read_text(encoding="utf-8"))
            mcp_servers = config.get("mcpServers", {})
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse MCP config %s: %s", mcp_config_path, e)
            return servers

        # Query each server concurrently with timeout
        tasks = []
        for server_name, server_config in mcp_servers.items():
            task = self._query_server_with_timeout(server_name, server_config)
            tasks.append(task)

        if tasks:
            servers = await asyncio.gather(*tasks, return_exceptions=False)

        return servers

    async def _query_server_with_timeout(
        self, server_name: str, server_config: dict
    ) -> MCPServerWithTools:
        """Query a single MCP server with timeout.

        Args:
            server_name: Name of the MCP server.
            server_config: Server configuration dictionary.

        Returns:
            MCPServerWithTools: Server with discovered tools or error.
        """
        try:
            result = await asyncio.wait_for(
                self._query_server(server_name, server_config),
                timeout=MCP_QUERY_TIMEOUT,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning("Timeout querying MCP server: %s", server_name)
            return MCPServerWithTools(
                name=server_name,
                connected=False,
                error=f"Timeout after {MCP_QUERY_TIMEOUT} seconds",
                tools=[],
            )
        except Exception as e:
            logger.warning("Error querying MCP server %s: %s", server_name, e)
            return MCPServerWithTools(
                name=server_name,
                connected=False,
                error=str(e),
                tools=[],
            )

    async def _query_server(
        self, server_name: str, server_config: dict
    ) -> MCPServerWithTools:
        """Query a single MCP server for its tools.

        Args:
            server_name: Name of the MCP server.
            server_config: Server configuration dictionary.

        Returns:
            MCPServerWithTools: Server with discovered tools.
        """
        # Check if it's HTTP or stdio server
        if "url" in server_config:
            return await self._query_http_server(server_name, server_config["url"])
        elif "command" in server_config:
            command = server_config["command"]
            args = server_config.get("args", [])
            env = server_config.get("env", {})
            return await self._query_stdio_server(server_name, command, args, env)
        else:
            return MCPServerWithTools(
                name=server_name,
                connected=False,
                error="No command or url specified",
                tools=[],
            )

    async def _query_http_server(self, server_name: str, url: str) -> MCPServerWithTools:
        """Query an HTTP MCP server for its tools.

        Args:
            server_name: Name of the MCP server.
            url: HTTP/HTTPS URL of the server.

        Returns:
            MCPServerWithTools: Server with discovered tools.
        """
        try:
            async with httpx.AsyncClient(timeout=MCP_QUERY_TIMEOUT) as client:
                # Send tools/list request
                response = await client.post(
                    url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "tools/list",
                        "id": 1,
                    },
                )
                response.raise_for_status()

                result = response.json()
                tools_data = result.get("result", {}).get("tools", [])

                # Convert to MCPToolInfo objects
                tools = [
                    MCPToolInfo(
                        name=tool["name"],
                        full_name=f"mcp__{server_name}__{tool['name']}",
                        description=tool.get("description"),
                    )
                    for tool in tools_data
                ]

                return MCPServerWithTools(
                    name=server_name,
                    connected=True,
                    tools=tools,
                )

        except httpx.HTTPError as e:
            logger.warning("HTTP error querying server %s: %s", server_name, e)
            return MCPServerWithTools(
                name=server_name,
                connected=False,
                error=f"HTTP error: {str(e)}",
                tools=[],
            )
        except Exception as e:
            logger.warning("Error querying HTTP server %s: %s", server_name, e)
            return MCPServerWithTools(
                name=server_name,
                connected=False,
                error=str(e),
                tools=[],
            )

    async def _query_stdio_server(
        self, server_name: str, command: str, args: list[str], env: dict
    ) -> MCPServerWithTools:
        """Query a stdio-based MCP server for its tools.

        Args:
            server_name: Name of the MCP server.
            command: Command to execute.
            args: Command arguments.
            env: Environment variables.

        Returns:
            MCPServerWithTools: Server with discovered tools.
        """
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._query_stdio_sync, command, args, env
            )

            if result is None:
                return MCPServerWithTools(
                    name=server_name,
                    connected=False,
                    error="Failed to communicate with server",
                    tools=[],
                )

            # Convert to MCPToolInfo objects
            tools = [
                MCPToolInfo(
                    name=tool["name"],
                    full_name=f"mcp__{server_name}__{tool['name']}",
                    description=tool.get("description"),
                )
                for tool in result
            ]

            return MCPServerWithTools(
                name=server_name,
                connected=True,
                tools=tools,
            )

        except Exception as e:
            logger.warning("Error querying stdio server %s: %s", server_name, e)
            return MCPServerWithTools(
                name=server_name,
                connected=False,
                error=str(e),
                tools=[],
            )

    def _query_stdio_sync(
        self, command: str, args: list[str], env: dict
    ) -> list[dict] | None:
        """Synchronously query a stdio MCP server.

        This method is run in an executor to avoid blocking the event loop.

        Args:
            command: Command to execute.
            args: Command arguments.
            env: Environment variables.

        Returns:
            list[dict] | None: List of tools or None on error.
        """
        proc = None  # Initialize before try block
        try:
            # Prepare environment variables
            import os

            proc_env = os.environ.copy()
            proc_env.update(env)

            # Start the process
            proc = subprocess.Popen(
                [command] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=proc_env,
            )

            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "claude-subagent-editor",
                        "version": "0.1.0",
                    },
                },
                "id": 1,
            }

            if proc.stdin:
                proc.stdin.write(json.dumps(init_request) + "\n")
                proc.stdin.flush()

            # Read initialize response
            if proc.stdout:
                init_response = proc.stdout.readline()
                if not init_response:
                    proc.terminate()
                    return None

            # Send tools/list request
            tools_request = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 2,
            }

            if proc.stdin:
                proc.stdin.write(json.dumps(tools_request) + "\n")
                proc.stdin.flush()

            # Read tools/list response
            if proc.stdout:
                tools_response = proc.stdout.readline()
                if not tools_response:
                    proc.terminate()
                    return None

                result = json.loads(tools_response)
                tools = result.get("result", {}).get("tools", [])

                # Clean up
                proc.terminate()
                proc.wait(timeout=1)

                return tools

            proc.terminate()
            return None

        except subprocess.TimeoutExpired:
            logger.warning("Subprocess timeout for command: %s", command)
            if proc is not None:
                proc.kill()
            return None
        except Exception as e:
            logger.warning("Error in stdio sync query: %s", e)
            if proc is not None:
                proc.terminate()
            return None
