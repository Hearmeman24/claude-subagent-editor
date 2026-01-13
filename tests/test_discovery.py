"""Tests for resource discovery service."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_subagent_editor.services.discovery import ResourceDiscovery


@pytest.fixture
def discovery():
    """Create a ResourceDiscovery instance."""
    return ResourceDiscovery()


class TestSkillDiscovery:
    """Test skill discovery functionality."""

    def test_discover_skills_no_plugins_dir(self, discovery: ResourceDiscovery, tmp_path: Path):
        """Test skill discovery when plugins directory doesn't exist."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            skills = discovery.discover_skills()
            assert skills == []

    def test_discover_skills_empty_plugins_dir(self, discovery: ResourceDiscovery, tmp_path: Path):
        """Test skill discovery with empty plugins directory."""
        plugins_dir = tmp_path / ".claude" / "plugins"
        plugins_dir.mkdir(parents=True)

        with patch("pathlib.Path.home", return_value=tmp_path):
            skills = discovery.discover_skills()
            assert skills == []

    def test_discover_skills_with_skill(self, discovery: ResourceDiscovery, tmp_path: Path):
        """Test discovering a skill with SKILL.md file."""
        # Create skill structure
        skill_dir = tmp_path / ".claude" / "plugins" / "my-plugin" / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)

        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("""---
name: my-skill
description: A test skill
---

# Skill content
""")

        with patch("pathlib.Path.home", return_value=tmp_path):
            skills = discovery.discover_skills()

            assert len(skills) == 1
            assert skills[0].name == "my-skill"
            assert skills[0].description == "A test skill"
            assert str(skill_file) in skills[0].path

    def test_discover_multiple_skills(self, discovery: ResourceDiscovery, tmp_path: Path):
        """Test discovering multiple skills."""
        # Create first skill
        skill1_dir = tmp_path / ".claude" / "plugins" / "plugin1" / "skills" / "skill-one"
        skill1_dir.mkdir(parents=True)
        (skill1_dir / "SKILL.md").write_text("""---
name: skill-one
description: First skill
---
""")

        # Create second skill
        skill2_dir = tmp_path / ".claude" / "plugins" / "plugin2" / "skills" / "skill-two"
        skill2_dir.mkdir(parents=True)
        (skill2_dir / "SKILL.md").write_text("""---
name: skill-two
---
""")

        with patch("pathlib.Path.home", return_value=tmp_path):
            skills = discovery.discover_skills()

            assert len(skills) == 2
            skill_names = {s.name for s in skills}
            assert skill_names == {"skill-one", "skill-two"}

    def test_discover_skill_without_frontmatter(self, discovery: ResourceDiscovery, tmp_path: Path):
        """Test skill discovery with SKILL.md without frontmatter."""
        skill_dir = tmp_path / ".claude" / "plugins" / "plugin" / "skills" / "no-frontmatter"
        skill_dir.mkdir(parents=True)

        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# Just markdown content\n\nNo frontmatter here.")

        with patch("pathlib.Path.home", return_value=tmp_path):
            skills = discovery.discover_skills()

            assert len(skills) == 1
            assert skills[0].name == "no-frontmatter"
            assert skills[0].description is None


class TestMCPServerDiscovery:
    """Test MCP server discovery functionality."""

    def test_discover_mcp_servers_success(self, discovery: ResourceDiscovery):
        """Test successful MCP server discovery."""
        mock_output = """playwright: npx @playwright/mcp@latest - ✓ Connected
context7: https://mcp.context7.com/mcp (HTTP) - ✓ Connected
shadcn: npx shadcn@latest mcp - Disconnected
"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            servers = discovery.discover_mcp_servers()

            assert len(servers) == 3

            # Check playwright server
            playwright = next((s for s in servers if s.name == "playwright"), None)
            assert playwright is not None
            assert playwright.command == "npx @playwright/mcp@latest"
            assert playwright.connected is True
            assert playwright.url is None

            # Check context7 server (HTTP)
            context7 = next((s for s in servers if s.name == "context7"), None)
            assert context7 is not None
            assert context7.url == "https://mcp.context7.com/mcp"
            assert context7.connected is True
            assert context7.command is None

            # Check shadcn server (disconnected)
            shadcn = next((s for s in servers if s.name == "shadcn"), None)
            assert shadcn is not None
            assert shadcn.command == "npx shadcn@latest mcp"
            assert shadcn.connected is False

    def test_discover_mcp_servers_command_not_found(self, discovery: ResourceDiscovery):
        """Test MCP server discovery when claude CLI is not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            servers = discovery.discover_mcp_servers()
            assert servers == []

    def test_discover_mcp_servers_command_fails(self, discovery: ResourceDiscovery):
        """Test MCP server discovery when command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: command failed"

        with patch("subprocess.run", return_value=mock_result):
            servers = discovery.discover_mcp_servers()
            assert servers == []

    def test_discover_mcp_servers_timeout(self, discovery: ResourceDiscovery):
        """Test MCP server discovery with timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 10)):
            servers = discovery.discover_mcp_servers()
            assert servers == []

    def test_parse_mcp_server_line_variations(self, discovery: ResourceDiscovery):
        """Test parsing various MCP server line formats."""
        # Test connected command server
        server = discovery._parse_mcp_server_line(
            "playwright: npx @playwright/mcp@latest - ✓ Connected"
        )
        assert server is not None
        assert server.name == "playwright"
        assert server.command == "npx @playwright/mcp@latest"
        assert server.connected is True

        # Test connected HTTP server
        server = discovery._parse_mcp_server_line(
            "context7: https://mcp.context7.com/mcp (HTTP) - ✓ Connected"
        )
        assert server is not None
        assert server.name == "context7"
        assert server.url == "https://mcp.context7.com/mcp"
        assert server.connected is True

        # Test disconnected server
        server = discovery._parse_mcp_server_line(
            "shadcn: npx shadcn@latest mcp - Disconnected"
        )
        assert server is not None
        assert server.name == "shadcn"
        assert server.connected is False

        # Test invalid line (no colon)
        server = discovery._parse_mcp_server_line("invalid line")
        assert server is None


class TestExtractSkillDescription:
    """Test skill description extraction."""

    def test_extract_description_with_quotes(self, discovery: ResourceDiscovery, tmp_path: Path):
        """Test extracting description with quotes."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("""---
name: test
description: "A description with quotes"
---
""")

        description = discovery._extract_skill_description(skill_file)
        assert description == "A description with quotes"

    def test_extract_description_without_quotes(self, discovery: ResourceDiscovery, tmp_path: Path):
        """Test extracting description without quotes."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("""---
name: test
description: A simple description
---
""")

        description = discovery._extract_skill_description(skill_file)
        assert description == "A simple description"

    def test_extract_description_no_frontmatter(self, discovery: ResourceDiscovery, tmp_path: Path):
        """Test extracting description from file without frontmatter."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("# Just content")

        description = discovery._extract_skill_description(skill_file)
        assert description is None

    def test_extract_description_missing_field(self, discovery: ResourceDiscovery, tmp_path: Path):
        """Test extracting description when field is missing."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("""---
name: test
---
""")

        description = discovery._extract_skill_description(skill_file)
        assert description is None
