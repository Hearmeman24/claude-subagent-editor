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

    def _load_mcp_configs(self, project_config_path: Path) -> dict[str, dict]:
        """Load MCP configs from both ~/.claude.json and project .mcp.json.

        Project config takes precedence over global config.

        Args:
            project_config_path: Path to project .mcp.json file.

        Returns:
            dict[str, dict]: Merged server configurations with headers.
        """
        configs: dict[str, dict] = {}

        # Load from ~/.claude.json first (lower precedence)
        global_config_path = Path.home() / ".claude.json"
        if global_config_path.exists():
            try:
                data = json.loads(global_config_path.read_text(encoding="utf-8"))
                for name, config in data.get("mcpServers", {}).items():
                    # Skip servers without url or command
                    if not config.get("url") and not config.get("command"):
                        logger.debug("Skipping server %s: no url or command", name)
                        continue
                    configs[name] = {
                        "url": config.get("url"),
                        "command": config.get("command"),
                        "args": config.get("args", []),
                        "env": config.get("env", {}),
                        "headers": config.get("headers", {}),
                        "transport": config.get("transport", "stdio"),
                    }
                logger.debug("Loaded %d servers from global config", len(configs))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Failed to parse global MCP config %s: %s", global_config_path, e)

        # Load from project .mcp.json (higher precedence - overrides global)
        if project_config_path.exists():
            try:
                data = json.loads(project_config_path.read_text(encoding="utf-8"))
                for name, config in data.get("mcpServers", {}).items():
                    # Skip servers without url or command
                    if not config.get("url") and not config.get("command"):
                        logger.debug("Skipping server %s: no url or command", name)
                        continue
                    configs[name] = {
                        "url": config.get("url"),
                        "command": config.get("command"),
                        "args": config.get("args", []),
                        "env": config.get("env", {}),
                        "headers": config.get("headers", {}),
                        "transport": config.get("transport", "stdio"),
                    }
                logger.debug("Loaded %d servers from project config", len(data.get("mcpServers", {})))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Failed to parse project MCP config %s: %s", project_config_path, e)

        return configs

    async def discover_all_tools(self, mcp_config_path: Path) -> list[MCPServerWithTools]:
        """Discover tools from all MCP servers in configuration.

        Args:
            mcp_config_path: Path to .mcp.json file.

        Returns:
            list[MCPServerWithTools]: List of servers with their tools.
        """
        servers: list[MCPServerWithTools] = []

        # Load MCP configurations from both global and project configs
        mcp_servers = self._load_mcp_configs(mcp_config_path)

        if not mcp_servers:
            logger.debug("No MCP servers configured")
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
        url = server_config.get("url")
        command = server_config.get("command")

        if url:
            headers = server_config.get("headers", {})
            return await self._query_http_server(server_name, url, headers)
        elif command:
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

    async def _query_http_server(
        self, server_name: str, url: str, custom_headers: dict | None = None
    ) -> MCPServerWithTools:
        """Query an HTTP MCP server for its tools.

        Args:
            server_name: Name of the MCP server.
            url: HTTP/HTTPS URL of the server.
            custom_headers: Optional custom headers from server config (e.g., API keys).

        Returns:
            MCPServerWithTools: Server with discovered tools.
        """
        try:
            async with httpx.AsyncClient(timeout=MCP_QUERY_TIMEOUT) as client:
                # MCP HTTP headers
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
                # Merge in custom headers from config (e.g., API keys)
                if custom_headers:
                    headers.update(custom_headers)

                # First, send initialize request (MCP protocol handshake)
                init_response = await client.post(
                    url,
                    json={
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
                    },
                    headers=headers,
                )
                init_response.raise_for_status()

                # Then send tools/list request
                tools_response = await client.post(
                    url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "tools/list",
                        "id": 2,
                    },
                    headers=headers,
                )
                tools_response.raise_for_status()

                result = tools_response.json()
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

        except httpx.HTTPStatusError as e:
            # Handle specific HTTP status errors
            logger.warning("HTTP %s error querying server %s: %s", e.response.status_code, server_name, e)
            if e.response.status_code == 406:
                # 406 Not Acceptable indicates SSE transport requirement - try SSE
                logger.info("Falling back to SSE transport for server %s", server_name)
                return await self._query_http_sse(url, server_name, custom_headers)
            else:
                error_msg = f"HTTP {e.response.status_code}: {str(e)}"
            return MCPServerWithTools(
                name=server_name,
                connected=False,
                error=error_msg,
                tools=[],
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

    async def _query_http_sse(
        self, url: str, server_name: str, custom_headers: dict | None = None
    ) -> MCPServerWithTools:
        """Query an HTTP MCP server using SSE (Server-Sent Events) transport.

        Args:
            url: HTTP/HTTPS URL of the server.
            server_name: Name of the MCP server.
            custom_headers: Optional custom headers from server config (e.g., API keys).

        Returns:
            MCPServerWithTools: Server with discovered tools.
        """
        try:
            from urllib.parse import urljoin

            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                # Step 1: Open SSE connection to get endpoint
                endpoint_path = None

                # Prepare SSE headers
                sse_headers = {"Accept": "text/event-stream"}
                if custom_headers:
                    sse_headers.update(custom_headers)

                async with client.stream(
                    "GET",
                    url,
                    headers=sse_headers
                ) as sse_response:
                    sse_response.raise_for_status()

                    # Parse SSE to find endpoint
                    event_type = None
                    async for line in sse_response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue

                        if line.startswith("event: "):
                            event_type = line[7:].strip()
                        elif line.startswith("data: "):
                            data = line[6:].strip()
                            if event_type == "endpoint":
                                endpoint_path = data
                                break
                            # Some servers may not send "event: endpoint" first
                            elif "sessionId" in data or data.startswith("/"):
                                endpoint_path = data
                                break

                if not endpoint_path:
                    return MCPServerWithTools(
                        name=server_name,
                        connected=False,
                        error="Could not get SSE endpoint",
                        tools=[],
                    )

                # Step 2: Build full endpoint URL
                message_url = urljoin(url, endpoint_path)
                logger.debug("SSE endpoint for %s: %s", server_name, message_url)

                # Prepare POST headers
                post_headers = {"Content-Type": "application/json"}
                if custom_headers:
                    post_headers.update(custom_headers)

                # Step 3: Send initialize request
                init_resp = await client.post(
                    message_url,
                    json={
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
                    },
                    headers=post_headers,
                )
                init_resp.raise_for_status()

                # Step 4: Send tools/list request
                tools_resp = await client.post(
                    message_url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "tools/list",
                        "id": 2,
                    },
                    headers=post_headers,
                )
                tools_resp.raise_for_status()

                # Parse tools from response
                tools_data = tools_resp.json()
                tools_list = tools_data.get("result", {}).get("tools", [])

                # Convert to MCPToolInfo objects
                tools = [
                    MCPToolInfo(
                        name=tool["name"],
                        full_name=f"mcp__{server_name}__{tool['name']}",
                        description=tool.get("description"),
                    )
                    for tool in tools_list
                ]

                return MCPServerWithTools(
                    name=server_name,
                    connected=True,
                    tools=tools,
                )

        except httpx.HTTPStatusError as e:
            logger.warning("SSE HTTP %s error querying server %s: %s", e.response.status_code, server_name, e)
            return MCPServerWithTools(
                name=server_name,
                connected=False,
                error=f"SSE HTTP {e.response.status_code}: {str(e)}",
                tools=[],
            )
        except httpx.HTTPError as e:
            logger.warning("SSE HTTP error querying server %s: %s", server_name, e)
            return MCPServerWithTools(
                name=server_name,
                connected=False,
                error=f"SSE HTTP error: {str(e)}",
                tools=[],
            )
        except Exception as e:
            logger.warning("SSE error querying server %s: %s", server_name, e)
            return MCPServerWithTools(
                name=server_name,
                connected=False,
                error=f"SSE error: {str(e)}",
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
