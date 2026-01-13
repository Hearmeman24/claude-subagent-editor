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

    result = await tool_discovery.discover_all_tools(config_path)

    assert result == []


@pytest.mark.asyncio
async def test_discover_all_tools_missing_file(tool_discovery, tmp_path):
    """Test discovering tools from non-existent config file."""
    config_path = tmp_path / "missing.json"

    result = await tool_discovery.discover_all_tools(config_path)

    assert result == []


@pytest.mark.asyncio
async def test_query_http_server_success(tool_discovery):
    """Test querying HTTP MCP server successfully."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {
            "tools": [
                {"name": "tool1", "description": "Test tool 1"},
                {"name": "tool2"},
            ]
        }
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
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
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {
            "tools": [
                {"name": "browser_click"},
                {"name": "browser_navigate"},
            ]
        }
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await tool_discovery._query_http_server(
            "playwright", "http://localhost:8080"
        )

        assert result.tools[0].full_name == "mcp__playwright__browser_click"
        assert result.tools[1].full_name == "mcp__playwright__browser_navigate"
