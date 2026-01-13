"""Tests for global resources endpoint."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client."""
    from claude_subagent_editor.main import app

    return TestClient(app)


class TestGlobalResourcesEndpoint:
    """Test the /api/resources/global endpoint."""

    def test_get_global_resources_empty(self, client: TestClient):
        """Test getting global resources when none are available."""
        # Mock discovery to return empty lists
        with patch(
            "claude_subagent_editor.api.routes._discovery.discover_skills", return_value=[]
        ), patch(
            "claude_subagent_editor.api.routes._discovery.discover_mcp_servers", return_value=[]
        ):
            response = client.get("/api/resources/global")

            assert response.status_code == 200
            data = response.json()

            assert "skills" in data
            assert "mcp_servers" in data
            assert data["skills"] == []
            assert data["mcp_servers"] == []

    def test_get_global_resources_with_skills(self, client: TestClient):
        """Test getting global resources with skills."""
        from claude_subagent_editor.services.discovery import DiscoveredSkill

        # Mock discovered skills
        mock_skills = [
            DiscoveredSkill(
                name="skill-one", path="/path/to/skill-one", description="First skill"
            ),
            DiscoveredSkill(name="skill-two", path="/path/to/skill-two", description=None),
        ]

        with patch(
            "claude_subagent_editor.api.routes._discovery.discover_skills",
            return_value=mock_skills,
        ), patch(
            "claude_subagent_editor.api.routes._discovery.discover_mcp_servers", return_value=[]
        ):
            response = client.get("/api/resources/global")

            assert response.status_code == 200
            data = response.json()

            assert len(data["skills"]) == 2
            assert data["skills"][0]["name"] == "skill-one"
            assert data["skills"][0]["path"] == "/path/to/skill-one"
            assert data["skills"][0]["description"] == "First skill"
            assert data["skills"][1]["name"] == "skill-two"
            assert data["skills"][1]["description"] is None

    def test_get_global_resources_with_mcp_servers(self, client: TestClient):
        """Test getting global resources with MCP servers."""
        from claude_subagent_editor.services.discovery import DiscoveredMCPServer

        # Mock discovered MCP servers
        mock_servers = [
            DiscoveredMCPServer(
                name="playwright",
                command="npx @playwright/mcp@latest",
                connected=True,
            ),
            DiscoveredMCPServer(
                name="context7",
                url="https://mcp.context7.com/mcp",
                connected=True,
            ),
        ]

        with patch(
            "claude_subagent_editor.api.routes._discovery.discover_skills", return_value=[]
        ), patch(
            "claude_subagent_editor.api.routes._discovery.discover_mcp_servers",
            return_value=mock_servers,
        ):
            response = client.get("/api/resources/global")

            assert response.status_code == 200
            data = response.json()

            assert len(data["mcp_servers"]) == 2

            # Check playwright server
            playwright = next(s for s in data["mcp_servers"] if s["name"] == "playwright")
            assert playwright["command"] == "npx @playwright/mcp@latest"
            assert playwright["connected"] is True
            assert playwright["url"] is None

            # Check context7 server
            context7 = next(s for s in data["mcp_servers"] if s["name"] == "context7")
            assert context7["url"] == "https://mcp.context7.com/mcp"
            assert context7["connected"] is True
            assert context7["command"] is None

    def test_get_global_resources_with_both(self, client: TestClient):
        """Test getting global resources with both skills and MCP servers."""
        from claude_subagent_editor.services.discovery import (
            DiscoveredMCPServer,
            DiscoveredSkill,
        )

        # Mock both
        mock_skills = [
            DiscoveredSkill(name="tdd", path="/path/to/tdd", description="TDD skill")
        ]
        mock_servers = [
            DiscoveredMCPServer(name="playwright", command="npx playwright", connected=True)
        ]

        with patch(
            "claude_subagent_editor.api.routes._discovery.discover_skills",
            return_value=mock_skills,
        ), patch(
            "claude_subagent_editor.api.routes._discovery.discover_mcp_servers",
            return_value=mock_servers,
        ):
            response = client.get("/api/resources/global")

            assert response.status_code == 200
            data = response.json()

            assert len(data["skills"]) == 1
            assert len(data["mcp_servers"]) == 1
            assert data["skills"][0]["name"] == "tdd"
            assert data["mcp_servers"][0]["name"] == "playwright"
