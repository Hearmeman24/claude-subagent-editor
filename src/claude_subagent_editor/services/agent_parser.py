"""Agent file parser - handles YAML frontmatter + markdown body."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


@dataclass
class ParsedAgent:
    """Parsed agent configuration from a markdown file."""

    filename: str
    name: str
    description: str
    model: str
    tools: list[str] | str = field(default_factory=list)  # Can be "*" for all tools
    skills: list[str] = field(default_factory=list)
    disallowed_tools: list[str] = field(default_factory=list)
    nickname: str | None = None
    body: str = ""
    raw_frontmatter: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "filename": self.filename,
            "name": self.name,
            "description": self.description,
            "model": self.model,
            "tools": self.tools,
            "skills": self.skills,
            "disallowed_tools": self.disallowed_tools,
            "nickname": self.nickname,
            "body": self.body,
        }


class AgentParser:
    """Parser for agent markdown files with YAML frontmatter."""

    FRONTMATTER_DELIMITER = "---"

    def __init__(self) -> None:
        """Initialize the YAML parser."""
        self._yaml = YAML()
        self._yaml.preserve_quotes = True

    def parse_file(self, file_path: Path) -> ParsedAgent:
        """Parse an agent file from disk."""
        content = file_path.read_text(encoding="utf-8")
        return self.parse_content(content, file_path.name)

    def parse_content(self, content: str, filename: str) -> ParsedAgent:
        """Parse agent content from a string."""
        frontmatter, body = self._split_frontmatter(content)
        data = self._parse_yaml(frontmatter)

        # Handle tools - can be list, string, or "*"
        tools_raw = data.get("tools", [])
        if tools_raw == "*":
            tools = "*"
        else:
            tools = self._normalize_list(tools_raw)

        # Parse disallowedTools
        disallowed_tools = self._normalize_list(data.get("disallowedTools", []))

        return ParsedAgent(
            filename=filename,
            name=self._get_required(data, "name"),
            description=self._get_required(data, "description"),
            model=data.get("model", "sonnet"),
            tools=tools,
            skills=self._normalize_list(data.get("skills", [])),
            disallowed_tools=disallowed_tools,
            nickname=data.get("nickname"),
            body=body.strip(),
            raw_frontmatter=dict(data),
        )

    def _split_frontmatter(self, content: str) -> tuple[str, str]:
        """Split content into frontmatter and body."""
        content = content.strip()

        if not content.startswith(self.FRONTMATTER_DELIMITER):
            raise ValueError("File must start with YAML frontmatter delimiter '---'")

        rest = content[len(self.FRONTMATTER_DELIMITER):]
        end_index = rest.find(f"\n{self.FRONTMATTER_DELIMITER}")

        if end_index == -1:
            raise ValueError("Missing closing YAML frontmatter delimiter '---'")

        frontmatter = rest[:end_index].strip()
        body = rest[end_index + len(self.FRONTMATTER_DELIMITER) + 1:].strip()

        if body.startswith("---"):
            body = body[3:].strip()
        elif body.startswith("\n"):
            body = body.lstrip("\n")

        return frontmatter, body

    def _parse_yaml(self, yaml_str: str) -> dict[str, Any]:
        """Parse YAML string to dictionary."""
        from io import StringIO

        try:
            result = self._yaml.load(StringIO(yaml_str))
            return result if result else {}
        except Exception as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}") from e

    def _get_required(self, data: dict[str, Any], key: str) -> str:
        """Get a required field from data."""
        value = data.get(key)
        if value is None:
            raise ValueError(f"Missing required field: {key}")
        return str(value)

    def _normalize_list(self, value: Any) -> list[str]:
        """Normalize a field that can be string or list to list."""
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [str(value)]

    def serialize(self, agent: ParsedAgent) -> str:
        """Serialize a ParsedAgent back to file content."""
        from io import StringIO

        frontmatter: dict[str, Any] = {
            "name": agent.name,
            "description": agent.description,
            "model": agent.model,
        }

        # Handle tools serialization
        if agent.tools == "*":
            frontmatter["tools"] = "*"
        elif agent.tools:
            frontmatter["tools"] = agent.tools

        if agent.skills:
            frontmatter["skills"] = agent.skills

        # Add disallowedTools if not empty
        if agent.disallowed_tools:
            frontmatter["disallowedTools"] = agent.disallowed_tools

        if agent.nickname:
            frontmatter["nickname"] = agent.nickname

        stream = StringIO()
        self._yaml.dump(frontmatter, stream)
        yaml_content = stream.getvalue()

        return f"---\n{yaml_content}---\n\n{agent.body}\n"
