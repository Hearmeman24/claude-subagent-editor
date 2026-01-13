"""Tests for agent parser service."""

import pytest
from pathlib import Path

from claude_subagent_editor.services.agent_parser import AgentParser, ParsedAgent


@pytest.fixture
def parser() -> AgentParser:
    """Create an AgentParser instance."""
    return AgentParser()


def test_parse_basic_agent(parser: AgentParser) -> None:
    """Test parsing a basic agent with required fields only."""
    content = """---
name: Test Agent
description: A test agent
model: claude-3-5-sonnet-20241022
---

This is the agent body.
"""
    result = parser.parse_content(content, "test.md")

    assert result.filename == "test.md"
    assert result.name == "Test Agent"
    assert result.description == "A test agent"
    assert result.model == "claude-3-5-sonnet-20241022"
    assert result.tools == []
    assert result.skills == []
    assert result.nickname is None
    assert result.body == "This is the agent body."


def test_parse_agent_with_tools_list(parser: AgentParser) -> None:
    """Test parsing an agent with tools as a list."""
    content = """---
name: Developer Agent
description: A development agent
model: claude-3-5-sonnet-20241022
tools:
  - read
  - write
  - edit
---

Developer body.
"""
    result = parser.parse_content(content, "dev.md")

    assert result.tools == ["read", "write", "edit"]


def test_parse_agent_with_tools_string(parser: AgentParser) -> None:
    """Test parsing an agent with tools as comma-separated string."""
    content = """---
name: Helper Agent
description: A helper agent
model: claude-3-5-sonnet-20241022
tools: read, write, edit
---

Helper body.
"""
    result = parser.parse_content(content, "helper.md")

    assert result.tools == ["read", "write", "edit"]


def test_parse_agent_with_skills(parser: AgentParser) -> None:
    """Test parsing an agent with skills."""
    content = """---
name: Skilled Agent
description: An agent with skills
model: claude-3-5-sonnet-20241022
skills:
  - python
  - javascript
  - typescript
---

Skilled body.
"""
    result = parser.parse_content(content, "skilled.md")

    assert result.skills == ["python", "javascript", "typescript"]


def test_parse_agent_with_nickname(parser: AgentParser) -> None:
    """Test parsing an agent with a nickname."""
    content = """---
name: Backend Developer
description: Python backend expert
model: claude-3-5-sonnet-20241022
nickname: Tessa
---

Backend body.
"""
    result = parser.parse_content(content, "backend.md")

    assert result.nickname == "Tessa"


def test_parse_missing_required_field(parser: AgentParser) -> None:
    """Test that parsing fails when required fields are missing."""
    content_missing_name = """---
description: Missing name
model: claude-3-5-sonnet-20241022
---

Body.
"""
    with pytest.raises(ValueError, match="Missing required field: name"):
        parser.parse_content(content_missing_name, "test.md")

    content_missing_description = """---
name: Test
model: claude-3-5-sonnet-20241022
---

Body.
"""
    with pytest.raises(ValueError, match="Missing required field: description"):
        parser.parse_content(content_missing_description, "test.md")


def test_parse_model_defaults_to_sonnet(parser: AgentParser) -> None:
    """Test that model field defaults to 'sonnet' when not provided."""
    content = """---
name: Test
description: Test description
---

Body.
"""
    result = parser.parse_content(content, "test.md")
    assert result.model == "sonnet"


def test_parse_missing_frontmatter_start(parser: AgentParser) -> None:
    """Test that parsing fails when frontmatter doesn't start with ---."""
    content = """name: Test
description: Test
model: test
---

Body.
"""
    with pytest.raises(ValueError, match="File must start with YAML frontmatter delimiter"):
        parser.parse_content(content, "test.md")


def test_parse_missing_frontmatter_end(parser: AgentParser) -> None:
    """Test that parsing fails when frontmatter doesn't have closing ---."""
    content = """---
name: Test
description: Test
model: test

Body.
"""
    with pytest.raises(ValueError, match="Missing closing YAML frontmatter delimiter"):
        parser.parse_content(content, "test.md")


def test_to_dict(parser: AgentParser) -> None:
    """Test conversion of ParsedAgent to dictionary."""
    content = """---
name: Test Agent
description: A test agent
model: claude-3-5-sonnet-20241022
tools:
  - read
  - write
nickname: TestBot
---

Test body.
"""
    result = parser.parse_content(content, "test.md")
    data = result.to_dict()

    assert data["filename"] == "test.md"
    assert data["name"] == "Test Agent"
    assert data["description"] == "A test agent"
    assert data["model"] == "claude-3-5-sonnet-20241022"
    assert data["tools"] == ["read", "write"]
    assert data["nickname"] == "TestBot"
    assert data["body"] == "Test body."


def test_serialize_roundtrip(parser: AgentParser) -> None:
    """Test that serialization and parsing produce consistent results."""
    original = ParsedAgent(
        filename="test.md",
        name="Test Agent",
        description="A test agent",
        model="claude-3-5-sonnet-20241022",
        tools=["read", "write"],
        skills=["python", "testing"],
        nickname="TestBot",
        body="This is the body content.",
    )

    serialized = parser.serialize(original)
    parsed = parser.parse_content(serialized, "test.md")

    assert parsed.name == original.name
    assert parsed.description == original.description
    assert parsed.model == original.model
    assert parsed.tools == original.tools
    assert parsed.skills == original.skills
    assert parsed.nickname == original.nickname
    assert parsed.body == original.body


def test_default_values() -> None:
    """Test that ParsedAgent has correct default values."""
    agent = ParsedAgent(
        filename="test.md",
        name="Test",
        description="Test description",
        model="test-model"
    )

    assert agent.tools == []
    assert agent.skills == []
    assert agent.nickname is None
    assert agent.body == ""
    assert agent.raw_frontmatter == {}


def test_parse_file(parser: AgentParser, tmp_path: Path) -> None:
    """Test parsing from an actual file on disk."""
    content = """---
name: File Agent
description: Agent from file
model: claude-3-5-sonnet-20241022
tools:
  - read
  - write
---

File body content.
"""
    test_file = tmp_path / "agent.md"
    test_file.write_text(content, encoding="utf-8")

    result = parser.parse_file(test_file)

    assert result.filename == "agent.md"
    assert result.name == "File Agent"
    assert result.description == "Agent from file"
    assert result.tools == ["read", "write"]
    assert result.body == "File body content."
