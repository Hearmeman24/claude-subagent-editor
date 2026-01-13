"""Tests for MCP tool discovery service."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_subagent_editor.services.mcp_tool_discovery import (
    MCPServerWithTools,
    MCPToolDiscovery,
    MCPToolInfo,
)


@pytest.fixture
def tool_discovery():
    """Create MCPToolDiscovery instance."""
    return MCPToolDiscovery()


@pytest.fixture
def temp_mcp_config(tmp_path):
    """Create a temporary .mcp.json file."""
    config = {
        "mcpServers": {
            "test-server": {
                "command": "python",
                "args": ["-m", "test.server"],
                "env": {"TEST_VAR": "value"},
            },
            "http-server": {
                "url": "http://localhost:8080/mcp",
            },
        }
    }
    config_path = tmp_path / ".mcp.json"
    config_path.write_text(json.dumps(config))
    return config_path


@pytest.mark.asyncio
async def test_discover_all_tools_empty_config(tool_discovery, tmp_path):
    """Test discovering tools from empty config."""
    config_path = tmp_path / ".mcp.json"
    config_path.write_text("{}")

    # Mock Path.home() to prevent loading from ~/.claude.json
    with patch("pathlib.Path.home") as mock_home:
        mock_home.return_value = tmp_path / "mock_home"
        result = await tool_discovery.discover_all_tools(config_path)

    assert result == []


@pytest.mark.asyncio
async def test_discover_all_tools_missing_file(tool_discovery, tmp_path):
    """Test discovering tools from non-existent config file."""
    config_path = tmp_path / "missing.json"

    # Mock Path.home() to prevent loading from ~/.claude.json
    with patch("pathlib.Path.home") as mock_home:
        mock_home.return_value = tmp_path / "mock_home"
        result = await tool_discovery.discover_all_tools(config_path)

    assert result == []


@pytest.mark.asyncio
async def test_query_http_server_success(tool_discovery):
    """Test querying HTTP MCP server successfully."""
    # Mock initialize response
    mock_init_response = MagicMock()
    mock_init_response.json.return_value = {"result": {"protocolVersion": "2024-11-05"}}

    # Mock tools/list response
    mock_tools_response = MagicMock()
    mock_tools_response.json.return_value = {
        "result": {
            "tools": [
                {"name": "tool1", "description": "Test tool 1"},
                {"name": "tool2"},
            ]
        }
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=[mock_init_response, mock_tools_response]
        )

        result = await tool_discovery._query_http_server("test", "http://localhost:8080")

        assert result.name == "test"
        assert result.connected is True
        assert result.error is None
        assert len(result.tools) == 2
        assert result.tools[0].name == "tool1"
        assert result.tools[0].full_name == "mcp__test__tool1"
        assert result.tools[0].description == "Test tool 1"
        assert result.tools[1].name == "tool2"
        assert result.tools[1].full_name == "mcp__test__tool2"


@pytest.mark.asyncio
async def test_query_http_server_error(tool_discovery):
    """Test querying HTTP MCP server with error."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=Exception("Connection error")
        )

        result = await tool_discovery._query_http_server("test", "http://localhost:8080")

        assert result.name == "test"
        assert result.connected is False
        assert "Connection error" in result.error
        assert result.tools == []


@pytest.mark.asyncio
async def test_query_http_server_406_falls_back_to_sse(tool_discovery):
    """Test querying HTTP MCP server with 406 falls back to SSE transport."""
    import httpx

    # Mock SSE success response
    mock_sse_result = MCPServerWithTools(
        name="test",
        connected=True,
        tools=[
            MCPToolInfo(
                name="sse_tool",
                full_name="mcp__test__sse_tool",
                description="SSE tool",
            )
        ],
    )

    with patch("httpx.AsyncClient") as mock_client:
        # Create a mock HTTPStatusError for 406
        mock_response = MagicMock()
        mock_response.status_code = 406
        mock_error = httpx.HTTPStatusError(
            "406 Not Acceptable", request=MagicMock(), response=mock_response
        )

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=mock_error
        )

        with patch.object(tool_discovery, "_query_http_sse", return_value=mock_sse_result):
            result = await tool_discovery._query_http_server("test", "http://localhost:8080")

            assert result.name == "test"
            assert result.connected is True
            assert len(result.tools) == 1
            assert result.tools[0].name == "sse_tool"


@pytest.mark.asyncio
async def test_query_http_sse_success(tool_discovery):
    """Test querying HTTP MCP server with SSE transport successfully."""

    # Mock SSE stream response
    async def mock_aiter_lines():
        """Mock SSE event stream."""
        yield "event: endpoint"
        yield "data: /message?sessionId=test123"
        yield ""

    mock_sse_response = MagicMock()
    mock_sse_response.aiter_lines = mock_aiter_lines
    mock_sse_response.raise_for_status = MagicMock()

    # Mock JSON-RPC responses
    mock_init_response = MagicMock()
    mock_init_response.json.return_value = {"result": {"protocolVersion": "2024-11-05"}}
    mock_init_response.raise_for_status = MagicMock()

    mock_tools_response = MagicMock()
    mock_tools_response.json.return_value = {
        "result": {
            "tools": [
                {"name": "sse_tool1", "description": "SSE tool 1"},
                {"name": "sse_tool2"},
            ]
        }
    }
    mock_tools_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = MagicMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Mock the stream method
        mock_client_instance.stream.return_value.__aenter__.return_value = mock_sse_response

        # Mock the post method for init and tools/list
        mock_client_instance.post = AsyncMock(
            side_effect=[mock_init_response, mock_tools_response]
        )

        result = await tool_discovery._query_http_sse("http://localhost:8080", "test-sse")

        assert result.name == "test-sse"
        assert result.connected is True
        assert result.error is None
        assert len(result.tools) == 2
        assert result.tools[0].name == "sse_tool1"
        assert result.tools[0].full_name == "mcp__test-sse__sse_tool1"
        assert result.tools[0].description == "SSE tool 1"
        assert result.tools[1].name == "sse_tool2"


@pytest.mark.asyncio
async def test_query_http_sse_no_endpoint(tool_discovery):
    """Test SSE transport when endpoint is not found."""

    # Mock SSE stream response with no endpoint
    async def mock_aiter_lines():
        """Mock SSE event stream without endpoint."""
        yield "event: message"
        yield "data: some other data"
        yield ""

    mock_sse_response = MagicMock()
    mock_sse_response.aiter_lines = mock_aiter_lines
    mock_sse_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = MagicMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        mock_client_instance.stream.return_value.__aenter__.return_value = mock_sse_response

        result = await tool_discovery._query_http_sse("http://localhost:8080", "test-sse")

        assert result.name == "test-sse"
        assert result.connected is False
        assert "Could not get SSE endpoint" in result.error
        assert result.tools == []


@pytest.mark.asyncio
async def test_query_server_with_timeout(tool_discovery):
    """Test that server queries timeout correctly."""

    async def slow_query(name, config):
        await asyncio.sleep(15)  # Longer than timeout
        return MCPServerWithTools(name=name, connected=True, tools=[])

    with patch.object(tool_discovery, "_query_server", side_effect=slow_query):
        result = await tool_discovery._query_server_with_timeout(
            "slow-server", {"command": "test"}
        )

        assert result.name == "slow-server"
        assert result.connected is False
        assert "Timeout" in result.error


@pytest.mark.asyncio
async def test_query_stdio_server_success(tool_discovery):
    """Test querying stdio MCP server successfully."""
    mock_tools = [
        {"name": "stdio_tool1", "description": "Stdio tool 1"},
        {"name": "stdio_tool2"},
    ]

    with patch.object(tool_discovery, "_query_stdio_sync", return_value=mock_tools):
        result = await tool_discovery._query_stdio_server(
            "stdio-server", "python", ["-m", "test"], {}
        )

        assert result.name == "stdio-server"
        assert result.connected is True
        assert result.error is None
        assert len(result.tools) == 2
        assert result.tools[0].name == "stdio_tool1"
        assert result.tools[0].full_name == "mcp__stdio-server__stdio_tool1"


@pytest.mark.asyncio
async def test_query_stdio_server_failure(tool_discovery):
    """Test querying stdio MCP server with failure."""
    with patch.object(tool_discovery, "_query_stdio_sync", return_value=None):
        result = await tool_discovery._query_stdio_server(
            "stdio-server", "python", ["-m", "test"], {}
        )

        assert result.name == "stdio-server"
        assert result.connected is False
        assert result.error == "Failed to communicate with server"
        assert result.tools == []


def test_query_stdio_sync_no_response(tool_discovery):
    """Test stdio sync query when process doesn't respond."""
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.readline.return_value = ""  # No response
        mock_popen.return_value = mock_proc

        result = tool_discovery._query_stdio_sync("python", ["-m", "test"], {})

        assert result is None
        mock_proc.terminate.assert_called()


def test_query_stdio_sync_valid_response(tool_discovery):
    """Test stdio sync query with valid response."""
    tools_response = {
        "result": {
            "tools": [
                {"name": "tool1", "description": "Test"},
            ]
        }
    }

    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.readline.side_effect = [
            '{"result": {}}\n',  # init response
            json.dumps(tools_response) + "\n",  # tools response
        ]
        mock_popen.return_value = mock_proc

        result = tool_discovery._query_stdio_sync("python", ["-m", "test"], {})

        assert result is not None
        assert len(result) == 1
        assert result[0]["name"] == "tool1"


@pytest.mark.asyncio
async def test_tool_naming_convention(tool_discovery):
    """Test that tool names follow the mcp__server__tool convention."""
    # Mock initialize response
    mock_init_response = MagicMock()
    mock_init_response.json.return_value = {"result": {"protocolVersion": "2024-11-05"}}

    # Mock tools/list response
    mock_tools_response = MagicMock()
    mock_tools_response.json.return_value = {
        "result": {
            "tools": [
                {"name": "browser_click"},
                {"name": "browser_navigate"},
            ]
        }
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=[mock_init_response, mock_tools_response]
        )

        result = await tool_discovery._query_http_server(
            "playwright", "http://localhost:8080"
        )

        assert result.tools[0].full_name == "mcp__playwright__browser_click"
        assert result.tools[1].full_name == "mcp__playwright__browser_navigate"


@pytest.mark.asyncio
async def test_query_http_server_with_custom_headers(tool_discovery):
    """Test that custom headers from config are passed to HTTP requests."""
    # Mock initialize response
    mock_init_response = MagicMock()
    mock_init_response.json.return_value = {"result": {"protocolVersion": "2024-11-05"}}

    # Mock tools/list response
    mock_tools_response = MagicMock()
    mock_tools_response.json.return_value = {
        "result": {
            "tools": [
                {"name": "tool1", "description": "Test tool 1"},
            ]
        }
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(side_effect=[mock_init_response, mock_tools_response])
        mock_client.return_value.__aenter__.return_value.post = mock_post

        custom_headers = {"CONTEXT7_API_KEY": "test-key-123"}
        result = await tool_discovery._query_http_server(
            "test", "http://localhost:8080", custom_headers
        )

        assert result.connected is True
        assert len(result.tools) == 1

        # Verify headers were included in both requests
        assert mock_post.call_count == 2
        for call in mock_post.call_args_list:
            headers = call.kwargs.get("headers", {})
            assert "CONTEXT7_API_KEY" in headers
            assert headers["CONTEXT7_API_KEY"] == "test-key-123"
            assert headers["Content-Type"] == "application/json"
            assert headers["Accept"] == "application/json"


@pytest.mark.asyncio
async def test_load_configs_merges_global_and_project(tool_discovery, tmp_path):
    """Test that configs from global and project are merged correctly."""
    # Create fake global config
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    global_config_path = fake_home / ".claude.json"
    global_config_path.write_text(
        json.dumps({
            "mcpServers": {
                "global-server": {
                    "url": "http://global.example.com",
                    "headers": {"API_KEY": "global-key"}
                }
            }
        })
    )

    # Create project config
    project_config_path = tmp_path / ".mcp.json"
    project_config_path.write_text(
        json.dumps({
            "mcpServers": {
                "project-server": {
                    "url": "http://project.example.com",
                    "headers": {"API_KEY": "project-key"}
                },
                "global-server": {
                    "url": "http://override.example.com",
                    "headers": {"API_KEY": "override-key"}
                }
            }
        })
    )

    with patch("pathlib.Path.home") as mock_home:
        mock_home.return_value = fake_home
        configs = tool_discovery._load_mcp_configs(project_config_path)

    # Should have both servers, with project overriding global for "global-server"
    assert len(configs) == 2
    assert "global-server" in configs
    assert "project-server" in configs
    assert configs["global-server"]["url"] == "http://override.example.com"
    assert configs["global-server"]["headers"]["API_KEY"] == "override-key"
    assert configs["project-server"]["url"] == "http://project.example.com"
    assert configs["project-server"]["headers"]["API_KEY"] == "project-key"
