"""Resource discovery service for skills and MCP servers."""

import json
import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredSkill:
    """Represents a discovered skill."""

    name: str
    path: str
    description: str | None = None


@dataclass
class DiscoveredMCPServer:
    """Represents a discovered MCP server."""

    name: str
    command: str | None = None
    url: str | None = None
    connected: bool = False


class ResourceDiscovery:
    """Service for discovering available skills and MCP servers."""

    def discover_skills(self) -> list[DiscoveredSkill]:
        """Discover skills from ~/.claude/plugins directory.

        Searches recursively for SKILL.md files. The skill name is the
        containing folder name.

        Example:
            ~/.claude/plugins/cache/foo-plugin/skills/my-skill/SKILL.md
            -> skill name is "my-skill"

        Returns:
            list[DiscoveredSkill]: List of discovered skills.
        """
        skills: list[DiscoveredSkill] = []
        plugins_dir = Path.home() / ".claude" / "plugins"

        if not plugins_dir.exists():
            logger.debug("Plugins directory does not exist: %s", plugins_dir)
            return skills

        # Find all SKILL.md files recursively
        for skill_file in plugins_dir.rglob("SKILL.md"):
            try:
                # The skill name is the containing directory name
                skill_name = skill_file.parent.name
                skill_path = str(skill_file)

                # Try to extract description from frontmatter
                description = self._extract_skill_description(skill_file)

                skills.append(
                    DiscoveredSkill(
                        name=skill_name,
                        path=skill_path,
                        description=description,
                    )
                )
                logger.debug("Discovered skill: %s at %s", skill_name, skill_path)
            except Exception as e:
                logger.warning("Error processing skill file %s: %s", skill_file, e)

        return sorted(skills, key=lambda s: s.name)

    def _extract_skill_description(self, skill_file: Path) -> str | None:
        """Extract description from skill file frontmatter.

        Args:
            skill_file: Path to SKILL.md file.

        Returns:
            str | None: Description if found, None otherwise.
        """
        try:
            content = skill_file.read_text(encoding="utf-8")

            # Check if file starts with frontmatter
            if not content.startswith("---"):
                return None

            # Find end of frontmatter
            end_marker = content.find("---", 3)
            if end_marker == -1:
                return None

            frontmatter = content[3:end_marker]

            # Simple extraction of description field
            for line in frontmatter.split("\n"):
                if line.strip().startswith("description:"):
                    desc = line.split(":", 1)[1].strip()
                    # Remove quotes if present
                    desc = desc.strip('"').strip("'")
                    return desc

            return None
        except Exception as e:
            logger.warning("Error extracting description from %s: %s", skill_file, e)
            return None

    def discover_mcp_servers(self) -> list[DiscoveredMCPServer]:
        """Discover MCP servers by running 'claude mcp list'.

        Parses the output to extract server name, command/url, and connection status.

        Example output:
            playwright: npx @playwright/mcp@latest - ✓ Connected
            context7: https://mcp.context7.com/mcp (HTTP) - ✓ Connected
            shadcn: npx shadcn@latest mcp - ✓ Connected

        Returns:
            list[DiscoveredMCPServer]: List of discovered MCP servers.
        """
        servers: list[DiscoveredMCPServer] = []

        try:
            # Run 'claude mcp list' command
            result = subprocess.run(
                ["claude", "mcp", "list"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if result.returncode != 0:
                logger.warning(
                    "claude mcp list command failed with code %s: %s",
                    result.returncode,
                    result.stderr,
                )
                return servers

            # Parse the output
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue

                # Parse line format: "name: command/url - status"
                server = self._parse_mcp_server_line(line)
                if server:
                    servers.append(server)
                    logger.debug(
                        "Discovered MCP server: %s (connected=%s)",
                        server.name,
                        server.connected,
                    )

        except subprocess.TimeoutExpired:
            logger.warning("claude mcp list command timed out")
        except FileNotFoundError:
            logger.debug("claude CLI not found, skipping MCP server discovery")
        except Exception as e:
            logger.warning("Error discovering MCP servers: %s", e)

        return sorted(servers, key=lambda s: s.name)

    def _parse_mcp_server_line(self, line: str) -> DiscoveredMCPServer | None:
        """Parse a single line from 'claude mcp list' output.

        Args:
            line: Line to parse.

        Returns:
            DiscoveredMCPServer | None: Parsed server or None if invalid.
        """
        try:
            # Pattern: "name: command/url - status"
            # Check for connection status
            connected = "✓ Connected" in line or "Connected" in line

            # Split on first colon to get name and rest
            if ":" not in line:
                return None

            name, rest = line.split(":", 1)
            name = name.strip()

            # Remove status indicator if present
            rest = rest.split("-")[0].strip()

            # Detect if it's a URL or command
            is_url = rest.startswith("http://") or rest.startswith("https://")

            # Remove (HTTP) or similar markers
            rest = re.sub(r"\s*\([^)]+\)\s*$", "", rest).strip()

            if is_url:
                return DiscoveredMCPServer(
                    name=name,
                    url=rest,
                    connected=connected,
                )
            else:
                return DiscoveredMCPServer(
                    name=name,
                    command=rest,
                    connected=connected,
                )

        except Exception as e:
            logger.warning("Error parsing MCP server line '%s': %s", line, e)
            return None
