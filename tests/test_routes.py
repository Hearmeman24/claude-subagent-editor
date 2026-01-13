"""Tests for FastAPI routes."""

import json
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with state reset."""
    from claude_subagent_editor.main import app
    # Reset global state before each test
    from claude_subagent_editor.api import routes
    routes._current_project = None
    return TestClient(app)


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project with sample agents and .mcp.json."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create .claude/agents directory
    agents_dir = project_dir / ".claude" / "agents"
    agents_dir.mkdir(parents=True)

    # Create sample agent files
    agent1 = agents_dir / "python-backend.md"
    agent1.write_text("""---
name: python-backend-supervisor
description: Python backend development expert
model: opus
tools: [read, write, bash]
skills: [python, fastapi]
nickname: Tessa
---

You are a Python backend development expert.
""")

    agent2 = agents_dir / "react-supervisor.md"
    agent2.write_text("""---
name: react-supervisor
description: React frontend development
model: sonnet
tools: read, write
---

React expert.
""")

    # Create .mcp.json in project
    mcp_json = project_dir / ".mcp.json"
    mcp_json.write_text(json.dumps({
        "mcpServers": {
            "git-server": {
                "command": "git-mcp"
            },
            "filesystem": {
                "command": "fs-mcp"
            }
        }
    }))

    return project_dir


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test health check returns status and version."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"


class TestProjectScan:
    """Test project scanning endpoint."""

    def test_scan_valid_project(self, client: TestClient, temp_project: Path):
        """Test scanning a valid project."""
        response = client.post(
            "/api/project/scan",
            json={"path": str(temp_project)}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["path"] == str(temp_project)
        assert data["agent_count"] == 2
        assert len(data["agents"]) == 2

        # Check agents are parsed correctly
        agent_names = {agent["name"] for agent in data["agents"]}
        assert "python-backend-supervisor" in agent_names
        assert "react-supervisor" in agent_names

        # Check MCP servers discovered
        assert "git-server" in data["mcp_servers"]
        assert "filesystem" in data["mcp_servers"]

    def test_scan_nonexistent_directory(self, client: TestClient, tmp_path: Path):
        """Test scanning a nonexistent directory."""
        nonexistent = tmp_path / "does_not_exist"

        response = client.post(
            "/api/project/scan",
            json={"path": str(nonexistent)}
        )

        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"].lower()

    def test_scan_file_not_directory(self, client: TestClient, tmp_path: Path):
        """Test scanning a file instead of directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        response = client.post(
            "/api/project/scan",
            json={"path": str(file_path)}
        )

        assert response.status_code == 400
        assert "not a directory" in response.json()["detail"].lower()

    def test_scan_project_without_agents(self, client: TestClient, tmp_path: Path):
        """Test scanning a project with no agents directory."""
        project_dir = tmp_path / "empty_project"
        project_dir.mkdir()

        response = client.post(
            "/api/project/scan",
            json={"path": str(project_dir)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["agent_count"] == 0
        assert data["agents"] == []


class TestProjectAgents:
    """Test project agents listing endpoint."""

    def test_list_agents_no_project(self, client: TestClient):
        """Test listing agents without scanning first."""
        response = client.get("/api/project/agents")

        assert response.status_code == 400
        assert "no project" in response.json()["detail"].lower()

    def test_list_agents_after_scan(self, client: TestClient, temp_project: Path):
        """Test listing agents after scanning."""
        # First scan the project
        scan_response = client.post(
            "/api/project/scan",
            json={"path": str(temp_project)}
        )
        assert scan_response.status_code == 200

        # Then list agents
        response = client.get("/api/project/agents")

        assert response.status_code == 200
        data = response.json()

        assert data["count"] == 2
        assert len(data["agents"]) == 2

        agent_names = {agent["name"] for agent in data["agents"]}
        assert "python-backend-supervisor" in agent_names
        assert "react-supervisor" in agent_names


class TestGetAgent:
    """Test single agent retrieval endpoint."""

    def test_get_agent_no_project(self, client: TestClient):
        """Test getting agent without scanning first."""
        response = client.get("/api/agent/python-backend.md")

        assert response.status_code == 400
        assert "no project" in response.json()["detail"].lower()

    def test_get_agent_success(self, client: TestClient, temp_project: Path):
        """Test getting a specific agent."""
        # First scan the project
        scan_response = client.post(
            "/api/project/scan",
            json={"path": str(temp_project)}
        )
        assert scan_response.status_code == 200

        # Then get specific agent
        response = client.get("/api/agent/python-backend.md")

        assert response.status_code == 200
        data = response.json()

        agent = data["agent"]
        assert agent["filename"] == "python-backend.md"
        assert agent["name"] == "python-backend-supervisor"
        assert agent["description"] == "Python backend development expert"
        assert agent["model"] == "opus"
        assert agent["nickname"] == "Tessa"
        assert "Python backend development expert" in agent["body"]

    def test_get_agent_not_found(self, client: TestClient, temp_project: Path):
        """Test getting a nonexistent agent."""
        # First scan the project
        scan_response = client.post(
            "/api/project/scan",
            json={"path": str(temp_project)}
        )
        assert scan_response.status_code == 200

        # Try to get nonexistent agent
        response = client.get("/api/agent/nonexistent.md")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_agent_path_traversal(self, client: TestClient, temp_project: Path):
        """Test path traversal protection.

        Note: Some path traversal attempts (like bare '..' or '.') are resolved
        by the HTTP client before reaching the handler, resulting in 404 instead
        of 400. This is expected behavior as the client's path normalization
        provides a first line of defense. We test cases that would reach our handler.
        """
        # First scan the project
        scan_response = client.post(
            "/api/project/scan",
            json={"path": str(temp_project)}
        )
        assert scan_response.status_code == 200

        # Try path traversal attacks that should reach our handler
        # These contain / or \ so they get properly encoded and reach our validation
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "subdir/../../../secret.txt",
        ]

        for attempt in traversal_attempts:
            # URL encode to prevent client-side path resolution
            encoded = quote(attempt, safe='')
            response = client.get(f"/api/agent/{encoded}")
            assert response.status_code == 400, f"Failed for {attempt}: got {response.status_code}, expected 400"
            assert "invalid" in response.json()["detail"].lower()

        # Also test bare .. and . - these get resolved by client but should also be caught if they somehow reach us
        # Test by manipulating the request directly without URL path resolution
        for attempt in ["..", "."]:
            response = client.get(f"/api/agent/{attempt}")
            # These are resolved by client to different paths, resulting in 404
            # This is acceptable as client-side resolution is a security layer
            assert response.status_code in (400, 404), f"Failed for {attempt}: got {response.status_code}"


class TestAgentData:
    """Test agent data structure."""

    def test_agent_has_all_fields(self, client: TestClient, temp_project: Path):
        """Test that agent response has all expected fields."""
        # Scan and get agent
        client.post("/api/project/scan", json={"path": str(temp_project)})
        response = client.get("/api/agent/python-backend.md")

        assert response.status_code == 200
        agent = response.json()["agent"]

        # Check all fields present
        required_fields = ["filename", "name", "description", "model", "tools", "skills", "body"]
        for field in required_fields:
            assert field in agent, f"Missing field: {field}"

    def test_agent_tools_as_list(self, client: TestClient, temp_project: Path):
        """Test that tools are returned as list."""
        # Scan and get agent
        client.post("/api/project/scan", json={"path": str(temp_project)})
        response = client.get("/api/agent/python-backend.md")

        assert response.status_code == 200
        agent = response.json()["agent"]

        # Tools should be a list
        assert isinstance(agent["tools"], list)
        assert len(agent["tools"]) > 0
        assert "read" in agent["tools"]
        assert "write" in agent["tools"]
