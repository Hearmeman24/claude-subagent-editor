# Phase 1: Core Infrastructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the foundational FastAPI backend and React frontend scaffold for Claude Subagent Editor

**Architecture:** Python backend serves REST API + static React build. Agent files are parsed from YAML frontmatter + markdown body using ruamel.yaml.

**Tech Stack:** FastAPI, React 18, Vite, TypeScript, ruamel.yaml, Pydantic, uv

---

## Task 1: Python Project Setup

### Objective
Initialize the Python project structure with uv and create the entry point.

### Files to Create

#### `pyproject.toml`
```toml
[project]
name = "claude-subagent-editor"
version = "0.1.0"
description = "Web-based editor for Claude Code subagent YAML configuration files"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "ruamel.yaml>=0.18.0",
    "pydantic>=2.5.0",
    "watchfiles>=0.21.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.26.0",
]

[project.scripts]
claude-subagent-editor = "claude_subagent_editor.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/claude_subagent_editor"]
```

#### `src/claude_subagent_editor/__init__.py`
```python
"""Claude Subagent Editor - Visual editor for Claude Code agent configurations."""

__version__ = "0.1.0"
```

#### `src/claude_subagent_editor/__main__.py`
```python
"""CLI entry point for Claude Subagent Editor."""

import argparse
import uvicorn


def main() -> None:
    """Start the Claude Subagent Editor server."""
    parser = argparse.ArgumentParser(
        description="Claude Subagent Editor - Visual editor for agent configurations"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to bind to (default: 8765)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    args = parser.parse_args()

    print(f"Starting Claude Subagent Editor at http://{args.host}:{args.port}")
    uvicorn.run(
        "claude_subagent_editor.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
```

#### `src/claude_subagent_editor/main.py` (minimal placeholder)
```python
"""FastAPI application for Claude Subagent Editor."""

from fastapi import FastAPI

app = FastAPI(
    title="Claude Subagent Editor",
    description="Visual editor for Claude Code agent configurations",
    version="0.1.0",
)


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}
```

### Directory Structure After Task 1
```
claude_subagent_editor/
├── pyproject.toml
└── src/
    └── claude_subagent_editor/
        ├── __init__.py
        ├── __main__.py
        └── main.py
```

### Commands to Run
```bash
# Initialize uv environment and install dependencies
uv sync

# Verify the CLI starts
uv run claude-subagent-editor --help

# Start the server (should show health endpoint)
uv run claude-subagent-editor &
sleep 2
curl http://127.0.0.1:8765/api/health
# Kill the background server
pkill -f "claude-subagent-editor"
```

### Expected Output
```json
{"status":"healthy","version":"0.1.0"}
```

### Commit Message
```
feat: initialize Python project with uv and FastAPI entry point

- Add pyproject.toml with FastAPI, uvicorn, ruamel.yaml dependencies
- Create src/claude_subagent_editor package structure
- Add __main__.py CLI entry point with host/port arguments
- Add minimal main.py with health check endpoint
```

---

## Task 2: Agent Parser Service

### Objective
Create the service that parses agent markdown files with YAML frontmatter.

### Files to Create

#### `src/claude_subagent_editor/services/__init__.py`
```python
"""Services for Claude Subagent Editor."""

from .agent_parser import AgentParser, ParsedAgent

__all__ = ["AgentParser", "ParsedAgent"]
```

#### `src/claude_subagent_editor/services/agent_parser.py`
```python
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
    tools: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
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
        """Parse an agent file from disk.

        Args:
            file_path: Path to the agent markdown file.

        Returns:
            ParsedAgent with parsed frontmatter and body.

        Raises:
            ValueError: If file has invalid format.
            FileNotFoundError: If file does not exist.
        """
        content = file_path.read_text(encoding="utf-8")
        return self.parse_content(content, file_path.name)

    def parse_content(self, content: str, filename: str) -> ParsedAgent:
        """Parse agent content from a string.

        Args:
            content: Raw file content with YAML frontmatter.
            filename: Name of the file (for reference).

        Returns:
            ParsedAgent with parsed frontmatter and body.

        Raises:
            ValueError: If content has invalid format.
        """
        frontmatter, body = self._split_frontmatter(content)
        data = self._parse_yaml(frontmatter)

        return ParsedAgent(
            filename=filename,
            name=self._get_required(data, "name"),
            description=self._get_required(data, "description"),
            model=self._get_required(data, "model"),
            tools=self._normalize_list(data.get("tools", [])),
            skills=self._normalize_list(data.get("skills", [])),
            nickname=data.get("nickname"),
            body=body.strip(),
            raw_frontmatter=dict(data),
        )

    def _split_frontmatter(self, content: str) -> tuple[str, str]:
        """Split content into frontmatter and body.

        Args:
            content: Raw file content.

        Returns:
            Tuple of (frontmatter_yaml, markdown_body).

        Raises:
            ValueError: If frontmatter delimiters are missing.
        """
        content = content.strip()

        if not content.startswith(self.FRONTMATTER_DELIMITER):
            raise ValueError("File must start with YAML frontmatter delimiter '---'")

        # Find the closing delimiter
        rest = content[len(self.FRONTMATTER_DELIMITER) :]
        end_index = rest.find(f"\n{self.FRONTMATTER_DELIMITER}")

        if end_index == -1:
            raise ValueError("Missing closing YAML frontmatter delimiter '---'")

        frontmatter = rest[:end_index].strip()
        body = rest[end_index + len(self.FRONTMATTER_DELIMITER) + 1 :].strip()

        # Handle case where body starts with newline after ---
        if body.startswith("---"):
            body = body[3:].strip()
        elif body.startswith("\n"):
            body = body.lstrip("\n")

        return frontmatter, body

    def _parse_yaml(self, yaml_str: str) -> dict[str, Any]:
        """Parse YAML string to dictionary.

        Args:
            yaml_str: YAML content string.

        Returns:
            Parsed dictionary.

        Raises:
            ValueError: If YAML is invalid.
        """
        from io import StringIO

        try:
            result = self._yaml.load(StringIO(yaml_str))
            return result if result else {}
        except Exception as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}") from e

    def _get_required(self, data: dict[str, Any], key: str) -> str:
        """Get a required field from data.

        Args:
            data: Parsed YAML data.
            key: Field name.

        Returns:
            Field value as string.

        Raises:
            ValueError: If field is missing.
        """
        value = data.get(key)
        if value is None:
            raise ValueError(f"Missing required field: {key}")
        return str(value)

    def _normalize_list(self, value: Any) -> list[str]:
        """Normalize a field that can be string or list to list.

        Args:
            value: Either a comma-separated string or list.

        Returns:
            List of strings.
        """
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [str(value)]

    def serialize(self, agent: ParsedAgent) -> str:
        """Serialize a ParsedAgent back to file content.

        Args:
            agent: The agent to serialize.

        Returns:
            Full file content with frontmatter and body.
        """
        from io import StringIO

        # Build frontmatter dict preserving order
        frontmatter: dict[str, Any] = {
            "name": agent.name,
            "description": agent.description,
            "model": agent.model,
        }

        if agent.tools:
            frontmatter["tools"] = agent.tools
        if agent.skills:
            frontmatter["skills"] = agent.skills
        if agent.nickname:
            frontmatter["nickname"] = agent.nickname

        # Serialize YAML
        stream = StringIO()
        self._yaml.dump(frontmatter, stream)
        yaml_content = stream.getvalue()

        return f"---\n{yaml_content}---\n\n{agent.body}\n"
```

#### `tests/__init__.py`
```python
"""Tests for Claude Subagent Editor."""
```

#### `tests/test_agent_parser.py`
```python
"""Tests for the agent parser service."""

import pytest
from claude_subagent_editor.services.agent_parser import AgentParser, ParsedAgent


class TestAgentParser:
    """Tests for AgentParser."""

    @pytest.fixture
    def parser(self) -> AgentParser:
        """Create a parser instance."""
        return AgentParser()

    def test_parse_basic_agent(self, parser: AgentParser) -> None:
        """Test parsing a basic agent file."""
        content = """---
name: architect
description: System design and architecture
model: opus
---

# Architect Agent

You are the architect.
"""
        agent = parser.parse_content(content, "architect.md")

        assert agent.filename == "architect.md"
        assert agent.name == "architect"
        assert agent.description == "System design and architecture"
        assert agent.model == "opus"
        assert agent.tools == []
        assert agent.skills == []
        assert "# Architect Agent" in agent.body

    def test_parse_agent_with_tools_list(self, parser: AgentParser) -> None:
        """Test parsing agent with tools as YAML list."""
        content = """---
name: frontend
description: Frontend development
model: sonnet
tools:
  - Read
  - Write
  - Edit
---

Body content.
"""
        agent = parser.parse_content(content, "frontend.md")

        assert agent.tools == ["Read", "Write", "Edit"]

    def test_parse_agent_with_tools_string(self, parser: AgentParser) -> None:
        """Test parsing agent with tools as comma-separated string."""
        content = """---
name: worker
description: Small tasks
model: haiku
tools: Read, Write, Bash
---

Body.
"""
        agent = parser.parse_content(content, "worker.md")

        assert agent.tools == ["Read", "Write", "Bash"]

    def test_parse_agent_with_skills(self, parser: AgentParser) -> None:
        """Test parsing agent with skills."""
        content = """---
name: tester
description: Test automation
model: sonnet
skills:
  - tdd
  - verification
---

Body.
"""
        agent = parser.parse_content(content, "tester.md")

        assert agent.skills == ["tdd", "verification"]

    def test_parse_agent_with_nickname(self, parser: AgentParser) -> None:
        """Test parsing agent with nickname."""
        content = """---
name: architect
description: Design systems
model: opus
nickname: Ada
---

Body.
"""
        agent = parser.parse_content(content, "architect.md")

        assert agent.nickname == "Ada"

    def test_parse_missing_required_field(self, parser: AgentParser) -> None:
        """Test that missing required fields raise ValueError."""
        content = """---
name: test
description: Missing model
---

Body.
"""
        with pytest.raises(ValueError, match="Missing required field: model"):
            parser.parse_content(content, "test.md")

    def test_parse_missing_frontmatter_start(self, parser: AgentParser) -> None:
        """Test that missing frontmatter delimiter raises ValueError."""
        content = """name: test
description: No delimiter
model: opus
---

Body.
"""
        with pytest.raises(ValueError, match="must start with YAML frontmatter"):
            parser.parse_content(content, "test.md")

    def test_parse_missing_frontmatter_end(self, parser: AgentParser) -> None:
        """Test that missing closing delimiter raises ValueError."""
        content = """---
name: test
description: No closing
model: opus

Body without closing delimiter.
"""
        with pytest.raises(ValueError, match="Missing closing YAML"):
            parser.parse_content(content, "test.md")

    def test_to_dict(self, parser: AgentParser) -> None:
        """Test ParsedAgent.to_dict() method."""
        content = """---
name: test
description: Test agent
model: opus
tools:
  - Read
nickname: Testy
---

Body here.
"""
        agent = parser.parse_content(content, "test.md")
        data = agent.to_dict()

        assert data["filename"] == "test.md"
        assert data["name"] == "test"
        assert data["description"] == "Test agent"
        assert data["model"] == "opus"
        assert data["tools"] == ["Read"]
        assert data["skills"] == []
        assert data["nickname"] == "Testy"
        assert "Body here" in data["body"]

    def test_serialize_roundtrip(self, parser: AgentParser) -> None:
        """Test that serialize produces valid content that can be re-parsed."""
        original_content = """---
name: architect
description: System design
model: opus
tools:
  - Read
  - Glob
skills:
  - tdd
nickname: Ada
---

# Architect

You are Ada.
"""
        agent = parser.parse_content(original_content, "architect.md")
        serialized = parser.serialize(agent)
        reparsed = parser.parse_content(serialized, "architect.md")

        assert reparsed.name == agent.name
        assert reparsed.description == agent.description
        assert reparsed.model == agent.model
        assert reparsed.tools == agent.tools
        assert reparsed.skills == agent.skills
        assert reparsed.nickname == agent.nickname


class TestParsedAgent:
    """Tests for ParsedAgent dataclass."""

    def test_default_values(self) -> None:
        """Test ParsedAgent default values."""
        agent = ParsedAgent(
            filename="test.md",
            name="test",
            description="Test",
            model="opus",
        )

        assert agent.tools == []
        assert agent.skills == []
        assert agent.nickname is None
        assert agent.body == ""
```

### Commands to Run
```bash
# Install dev dependencies
uv sync --extra dev

# Run parser tests
uv run pytest tests/test_agent_parser.py -v
```

### Expected Output
```
tests/test_agent_parser.py::TestAgentParser::test_parse_basic_agent PASSED
tests/test_agent_parser.py::TestAgentParser::test_parse_agent_with_tools_list PASSED
tests/test_agent_parser.py::TestAgentParser::test_parse_agent_with_tools_string PASSED
tests/test_agent_parser.py::TestAgentParser::test_parse_agent_with_skills PASSED
tests/test_agent_parser.py::TestAgentParser::test_parse_agent_with_nickname PASSED
tests/test_agent_parser.py::TestAgentParser::test_parse_missing_required_field PASSED
tests/test_agent_parser.py::TestAgentParser::test_parse_missing_frontmatter_start PASSED
tests/test_agent_parser.py::TestAgentParser::test_parse_missing_frontmatter_end PASSED
tests/test_agent_parser.py::TestAgentParser::test_to_dict PASSED
tests/test_agent_parser.py::TestAgentParser::test_serialize_roundtrip PASSED
tests/test_agent_parser.py::TestParsedAgent::test_default_values PASSED
```

### Commit Message
```
feat: add agent parser service for YAML frontmatter + markdown

- Create AgentParser class using ruamel.yaml
- Support tools/skills as lists or comma-separated strings
- Add ParsedAgent dataclass with to_dict() and serialization
- Full test coverage for parsing and edge cases
```

---

## Task 3: Pydantic Models

### Objective
Create Pydantic schemas for API request/response validation.

### Files to Create

#### `src/claude_subagent_editor/models/__init__.py`
```python
"""Pydantic models for Claude Subagent Editor."""

from .schemas import (
    AgentConfig,
    AgentListResponse,
    AgentResponse,
    HealthResponse,
    ProjectScanRequest,
    ProjectScanResponse,
    ToolConfig,
    SkillConfig,
)

__all__ = [
    "AgentConfig",
    "AgentListResponse",
    "AgentResponse",
    "HealthResponse",
    "ProjectScanRequest",
    "ProjectScanResponse",
    "ToolConfig",
    "SkillConfig",
]
```

#### `src/claude_subagent_editor/models/schemas.py`
```python
"""Pydantic schemas for API validation."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ModelType(str, Enum):
    """Valid Claude model types."""

    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"


class ToolType(str, Enum):
    """Types of tools available."""

    BASE = "base"
    MCP = "mcp"


class ToolConfig(BaseModel):
    """Configuration for a tool."""

    name: str = Field(..., description="Tool name or identifier")
    tool_type: ToolType = Field(..., description="Type of tool (base or mcp)")
    mcp_server: str | None = Field(None, description="MCP server name if MCP tool")
    description: str | None = Field(None, description="Tool description")

    model_config = {"extra": "forbid"}


class SkillConfig(BaseModel):
    """Configuration for a skill."""

    name: str = Field(..., description="Skill name/identifier")
    description: str | None = Field(None, description="Skill description")
    path: str | None = Field(None, description="Path to skill file")

    model_config = {"extra": "forbid"}


class AgentConfig(BaseModel):
    """Full agent configuration."""

    filename: str = Field(..., description="Filename of the agent (e.g., architect.md)")
    name: str = Field(..., description="Agent identifier")
    description: str = Field(..., description="What the agent does")
    model: ModelType = Field(..., description="Claude model to use")
    tools: list[str] = Field(default_factory=list, description="Assigned tools")
    skills: list[str] = Field(default_factory=list, description="Assigned skills")
    nickname: str | None = Field(None, description="Friendly name for the agent")
    body: str = Field(default="", description="Markdown body content")

    model_config = {"extra": "forbid"}


class HealthResponse(BaseModel):
    """Response for health check endpoint."""

    status: Literal["healthy"] = "healthy"
    version: str = Field(..., description="Application version")

    model_config = {"extra": "forbid"}


class ProjectScanRequest(BaseModel):
    """Request to scan a project directory."""

    path: str = Field(..., description="Absolute path to project directory")

    model_config = {"extra": "forbid"}


class ProjectScanResponse(BaseModel):
    """Response from scanning a project."""

    path: str = Field(..., description="Scanned project path")
    agents: list[AgentConfig] = Field(
        default_factory=list, description="Discovered agents"
    )
    mcp_servers: list[str] = Field(
        default_factory=list, description="Discovered MCP server names"
    )
    agent_count: int = Field(..., description="Number of agents found")

    model_config = {"extra": "forbid"}


class AgentListResponse(BaseModel):
    """Response for listing agents."""

    agents: list[AgentConfig] = Field(..., description="List of agents")
    count: int = Field(..., description="Total count")

    model_config = {"extra": "forbid"}


class AgentResponse(BaseModel):
    """Response for single agent."""

    agent: AgentConfig = Field(..., description="Agent configuration")

    model_config = {"extra": "forbid"}
```

#### `tests/test_schemas.py`
```python
"""Tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from claude_subagent_editor.models.schemas import (
    AgentConfig,
    HealthResponse,
    ModelType,
    ProjectScanRequest,
    ProjectScanResponse,
    SkillConfig,
    ToolConfig,
    ToolType,
)


class TestAgentConfig:
    """Tests for AgentConfig schema."""

    def test_valid_agent_config(self) -> None:
        """Test creating a valid agent config."""
        agent = AgentConfig(
            filename="architect.md",
            name="architect",
            description="System design",
            model=ModelType.OPUS,
            tools=["Read", "Write"],
            skills=["tdd"],
            nickname="Ada",
            body="# Architect\n\nYou are Ada.",
        )

        assert agent.filename == "architect.md"
        assert agent.name == "architect"
        assert agent.model == ModelType.OPUS
        assert agent.tools == ["Read", "Write"]

    def test_agent_config_defaults(self) -> None:
        """Test AgentConfig default values."""
        agent = AgentConfig(
            filename="test.md",
            name="test",
            description="Test agent",
            model=ModelType.SONNET,
        )

        assert agent.tools == []
        assert agent.skills == []
        assert agent.nickname is None
        assert agent.body == ""

    def test_agent_config_model_string(self) -> None:
        """Test that model accepts string values."""
        agent = AgentConfig(
            filename="test.md",
            name="test",
            description="Test",
            model="opus",  # type: ignore - testing string coercion
        )

        assert agent.model == ModelType.OPUS

    def test_agent_config_invalid_model(self) -> None:
        """Test that invalid model raises ValidationError."""
        with pytest.raises(ValidationError):
            AgentConfig(
                filename="test.md",
                name="test",
                description="Test",
                model="invalid",  # type: ignore
            )

    def test_agent_config_missing_required(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            AgentConfig(
                filename="test.md",
                name="test",
                # missing description and model
            )  # type: ignore

    def test_agent_config_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            AgentConfig(
                filename="test.md",
                name="test",
                description="Test",
                model=ModelType.OPUS,
                unknown_field="value",  # type: ignore
            )


class TestToolConfig:
    """Tests for ToolConfig schema."""

    def test_base_tool(self) -> None:
        """Test creating a base tool config."""
        tool = ToolConfig(
            name="Read",
            tool_type=ToolType.BASE,
            description="Read files",
        )

        assert tool.name == "Read"
        assert tool.tool_type == ToolType.BASE
        assert tool.mcp_server is None

    def test_mcp_tool(self) -> None:
        """Test creating an MCP tool config."""
        tool = ToolConfig(
            name="browser_click",
            tool_type=ToolType.MCP,
            mcp_server="playwright",
            description="Click browser elements",
        )

        assert tool.tool_type == ToolType.MCP
        assert tool.mcp_server == "playwright"


class TestSkillConfig:
    """Tests for SkillConfig schema."""

    def test_skill_config(self) -> None:
        """Test creating a skill config."""
        skill = SkillConfig(
            name="tdd",
            description="Test-driven development",
            path="~/.claude/skills/tdd/SKILL.md",
        )

        assert skill.name == "tdd"
        assert skill.path is not None


class TestProjectScanRequest:
    """Tests for ProjectScanRequest schema."""

    def test_valid_request(self) -> None:
        """Test creating a valid scan request."""
        request = ProjectScanRequest(path="/Users/test/project")

        assert request.path == "/Users/test/project"

    def test_missing_path(self) -> None:
        """Test that missing path raises ValidationError."""
        with pytest.raises(ValidationError):
            ProjectScanRequest()  # type: ignore


class TestProjectScanResponse:
    """Tests for ProjectScanResponse schema."""

    def test_empty_response(self) -> None:
        """Test response with no agents."""
        response = ProjectScanResponse(
            path="/test",
            agents=[],
            mcp_servers=[],
            agent_count=0,
        )

        assert response.agent_count == 0

    def test_response_with_agents(self) -> None:
        """Test response with agents."""
        agent = AgentConfig(
            filename="test.md",
            name="test",
            description="Test",
            model=ModelType.OPUS,
        )
        response = ProjectScanResponse(
            path="/test",
            agents=[agent],
            mcp_servers=["playwright"],
            agent_count=1,
        )

        assert len(response.agents) == 1
        assert response.mcp_servers == ["playwright"]


class TestHealthResponse:
    """Tests for HealthResponse schema."""

    def test_health_response(self) -> None:
        """Test creating health response."""
        response = HealthResponse(version="0.1.0")

        assert response.status == "healthy"
        assert response.version == "0.1.0"


class TestModelType:
    """Tests for ModelType enum."""

    def test_all_model_types(self) -> None:
        """Test all valid model types."""
        assert ModelType.OPUS.value == "opus"
        assert ModelType.SONNET.value == "sonnet"
        assert ModelType.HAIKU.value == "haiku"
```

### Commands to Run
```bash
# Run schema tests
uv run pytest tests/test_schemas.py -v
```

### Expected Output
```
tests/test_schemas.py::TestAgentConfig::test_valid_agent_config PASSED
tests/test_schemas.py::TestAgentConfig::test_agent_config_defaults PASSED
tests/test_schemas.py::TestAgentConfig::test_agent_config_model_string PASSED
tests/test_schemas.py::TestAgentConfig::test_agent_config_invalid_model PASSED
tests/test_schemas.py::TestAgentConfig::test_agent_config_missing_required PASSED
tests/test_schemas.py::TestAgentConfig::test_agent_config_extra_fields_forbidden PASSED
tests/test_schemas.py::TestToolConfig::test_base_tool PASSED
tests/test_schemas.py::TestToolConfig::test_mcp_tool PASSED
tests/test_schemas.py::TestSkillConfig::test_skill_config PASSED
tests/test_schemas.py::TestProjectScanRequest::test_valid_request PASSED
tests/test_schemas.py::TestProjectScanRequest::test_missing_path PASSED
tests/test_schemas.py::TestProjectScanResponse::test_empty_response PASSED
tests/test_schemas.py::TestProjectScanResponse::test_response_with_agents PASSED
tests/test_schemas.py::TestHealthResponse::test_health_response PASSED
tests/test_schemas.py::TestModelType::test_all_model_types PASSED
```

### Commit Message
```
feat: add Pydantic schemas for API validation

- Add AgentConfig, ToolConfig, SkillConfig models
- Add request/response schemas for all endpoints
- Add ModelType enum (opus, sonnet, haiku)
- Full test coverage for validation rules
```

---

## Task 4: FastAPI Application

### Objective
Create the complete FastAPI application with all REST endpoints.

### Files to Create/Update

#### `src/claude_subagent_editor/api/__init__.py`
```python
"""API module for Claude Subagent Editor."""

from .routes import router

__all__ = ["router"]
```

#### `src/claude_subagent_editor/api/routes.py`
```python
"""REST API routes for Claude Subagent Editor."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from claude_subagent_editor.models.schemas import (
    AgentConfig,
    AgentListResponse,
    AgentResponse,
    HealthResponse,
    ModelType,
    ProjectScanRequest,
    ProjectScanResponse,
)
from claude_subagent_editor.services.agent_parser import AgentParser

router = APIRouter(prefix="/api", tags=["api"])

# Global state for current project (will be replaced with proper state management)
_current_project: Path | None = None
_parser = AgentParser()


def _get_project_path() -> Path:
    """Get current project path or raise error."""
    if _current_project is None:
        raise HTTPException(
            status_code=400,
            detail="No project loaded. Call POST /api/project/scan first.",
        )
    return _current_project


def _get_agents_dir(project_path: Path) -> Path:
    """Get the agents directory for a project."""
    return project_path / ".claude" / "agents"


def _parse_agent_file(file_path: Path) -> AgentConfig:
    """Parse an agent file to AgentConfig."""
    parsed = _parser.parse_file(file_path)
    return AgentConfig(
        filename=parsed.filename,
        name=parsed.name,
        description=parsed.description,
        model=ModelType(parsed.model),
        tools=parsed.tools,
        skills=parsed.skills,
        nickname=parsed.nickname,
        body=parsed.body,
    )


def _discover_mcp_servers(project_path: Path) -> list[str]:
    """Discover MCP servers from project and global config."""
    servers: list[str] = []

    # Check project .mcp.json
    project_mcp = project_path / ".mcp.json"
    if project_mcp.exists():
        try:
            data = json.loads(project_mcp.read_text())
            if "mcpServers" in data:
                servers.extend(data["mcpServers"].keys())
        except (json.JSONDecodeError, KeyError):
            pass

    # Check global ~/.claude/mcp.json
    global_mcp = Path.home() / ".claude" / "mcp.json"
    if global_mcp.exists():
        try:
            data = json.loads(global_mcp.read_text())
            if "mcpServers" in data:
                for name in data["mcpServers"].keys():
                    if name not in servers:
                        servers.append(name)
        except (json.JSONDecodeError, KeyError):
            pass

    return servers


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    from claude_subagent_editor import __version__

    return HealthResponse(version=__version__)


@router.post("/project/scan", response_model=ProjectScanResponse)
async def scan_project(request: ProjectScanRequest) -> ProjectScanResponse:
    """Scan a project directory for agents."""
    global _current_project

    project_path = Path(request.path).expanduser().resolve()

    if not project_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Directory not found: {request.path}",
        )

    if not project_path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a directory: {request.path}",
        )

    agents_dir = _get_agents_dir(project_path)
    agents: list[AgentConfig] = []

    if agents_dir.exists():
        for agent_file in sorted(agents_dir.glob("*.md")):
            try:
                agent = _parse_agent_file(agent_file)
                agents.append(agent)
            except ValueError as e:
                # Log but skip invalid files
                print(f"Warning: Skipping invalid agent file {agent_file}: {e}")

    mcp_servers = _discover_mcp_servers(project_path)

    # Update current project
    _current_project = project_path

    return ProjectScanResponse(
        path=str(project_path),
        agents=agents,
        mcp_servers=mcp_servers,
        agent_count=len(agents),
    )


@router.get("/project/agents", response_model=AgentListResponse)
async def list_agents() -> AgentListResponse:
    """List all agents in the current project."""
    project_path = _get_project_path()
    agents_dir = _get_agents_dir(project_path)
    agents: list[AgentConfig] = []

    if agents_dir.exists():
        for agent_file in sorted(agents_dir.glob("*.md")):
            try:
                agent = _parse_agent_file(agent_file)
                agents.append(agent)
            except ValueError:
                pass

    return AgentListResponse(agents=agents, count=len(agents))


@router.get("/agent/{filename}", response_model=AgentResponse)
async def get_agent(filename: str) -> AgentResponse:
    """Get a single agent by filename."""
    project_path = _get_project_path()
    agents_dir = _get_agents_dir(project_path)

    # Security: prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    agent_file = agents_dir / filename

    if not agent_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Agent not found: {filename}",
        )

    try:
        agent = _parse_agent_file(agent_file)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid agent file: {e}",
        )

    return AgentResponse(agent=agent)
```

#### `src/claude_subagent_editor/main.py` (update)
```python
"""FastAPI application for Claude Subagent Editor."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from claude_subagent_editor.api.routes import router

app = FastAPI(
    title="Claude Subagent Editor",
    description="Visual editor for Claude Code agent configurations",
    version="0.1.0",
)

# CORS configuration for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:8765",
        "http://127.0.0.1:8765",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Serve static files if they exist (built React app)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
```

#### `tests/test_routes.py`
```python
"""Tests for API routes."""

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from claude_subagent_editor.main import app
from claude_subagent_editor.api import routes


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    # Reset global state before each test
    routes._current_project = None
    return TestClient(app)


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project with agent files."""
    # Create agents directory
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)

    # Create sample agent files
    (agents_dir / "architect.md").write_text("""---
name: architect
description: System design and architecture
model: opus
tools:
  - Read
  - Glob
nickname: Ada
---

# Architect

You are Ada the architect.
""")

    (agents_dir / "worker.md").write_text("""---
name: worker
description: Small tasks
model: haiku
tools: Read, Write
---

# Worker

A simple worker.
""")

    # Create .mcp.json
    mcp_config = {
        "mcpServers": {
            "playwright": {"command": "npx", "args": ["playwright"]},
            "context7": {"command": "context7"},
        }
    }
    (tmp_path / ".mcp.json").write_text(json.dumps(mcp_config))

    return tmp_path


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Test health check returns healthy status."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestProjectScan:
    """Tests for /api/project/scan endpoint."""

    def test_scan_valid_project(
        self, client: TestClient, temp_project: Path
    ) -> None:
        """Test scanning a valid project directory."""
        response = client.post(
            "/api/project/scan",
            json={"path": str(temp_project)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["path"] == str(temp_project)
        assert data["agent_count"] == 2
        assert len(data["agents"]) == 2
        assert "playwright" in data["mcp_servers"]
        assert "context7" in data["mcp_servers"]

    def test_scan_nonexistent_directory(self, client: TestClient) -> None:
        """Test scanning nonexistent directory returns 404."""
        response = client.post(
            "/api/project/scan",
            json={"path": "/nonexistent/path/to/project"},
        )

        assert response.status_code == 404

    def test_scan_file_not_directory(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Test scanning a file (not directory) returns 400."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("hello")

        response = client.post(
            "/api/project/scan",
            json={"path": str(file_path)},
        )

        assert response.status_code == 400

    def test_scan_project_without_agents(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Test scanning project with no agents directory."""
        response = client.post(
            "/api/project/scan",
            json={"path": str(tmp_path)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["agent_count"] == 0
        assert data["agents"] == []


class TestProjectAgents:
    """Tests for /api/project/agents endpoint."""

    def test_list_agents_no_project(self, client: TestClient) -> None:
        """Test listing agents when no project is loaded."""
        response = client.get("/api/project/agents")

        assert response.status_code == 400
        assert "No project loaded" in response.json()["detail"]

    def test_list_agents_after_scan(
        self, client: TestClient, temp_project: Path
    ) -> None:
        """Test listing agents after scanning."""
        # First scan the project
        client.post("/api/project/scan", json={"path": str(temp_project)})

        # Then list agents
        response = client.get("/api/project/agents")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        agent_names = [a["name"] for a in data["agents"]]
        assert "architect" in agent_names
        assert "worker" in agent_names


class TestGetAgent:
    """Tests for /api/agent/{filename} endpoint."""

    def test_get_agent_no_project(self, client: TestClient) -> None:
        """Test getting agent when no project loaded."""
        response = client.get("/api/agent/architect.md")

        assert response.status_code == 400

    def test_get_agent_success(
        self, client: TestClient, temp_project: Path
    ) -> None:
        """Test getting a specific agent."""
        client.post("/api/project/scan", json={"path": str(temp_project)})

        response = client.get("/api/agent/architect.md")

        assert response.status_code == 200
        agent = response.json()["agent"]
        assert agent["name"] == "architect"
        assert agent["model"] == "opus"
        assert agent["nickname"] == "Ada"
        assert "Read" in agent["tools"]

    def test_get_agent_not_found(
        self, client: TestClient, temp_project: Path
    ) -> None:
        """Test getting nonexistent agent."""
        client.post("/api/project/scan", json={"path": str(temp_project)})

        response = client.get("/api/agent/nonexistent.md")

        assert response.status_code == 404

    def test_get_agent_path_traversal(
        self, client: TestClient, temp_project: Path
    ) -> None:
        """Test that path traversal is blocked."""
        client.post("/api/project/scan", json={"path": str(temp_project)})

        response = client.get("/api/agent/../../../etc/passwd")

        assert response.status_code == 400
        assert "Invalid filename" in response.json()["detail"]


class TestAgentData:
    """Tests for agent data structure."""

    def test_agent_has_all_fields(
        self, client: TestClient, temp_project: Path
    ) -> None:
        """Test that agent response has all expected fields."""
        client.post("/api/project/scan", json={"path": str(temp_project)})

        response = client.get("/api/agent/architect.md")
        agent = response.json()["agent"]

        assert "filename" in agent
        assert "name" in agent
        assert "description" in agent
        assert "model" in agent
        assert "tools" in agent
        assert "skills" in agent
        assert "nickname" in agent
        assert "body" in agent

    def test_agent_tools_as_list(
        self, client: TestClient, temp_project: Path
    ) -> None:
        """Test that tools are always returned as list."""
        client.post("/api/project/scan", json={"path": str(temp_project)})

        # worker.md has tools as comma-separated string
        response = client.get("/api/agent/worker.md")
        agent = response.json()["agent"]

        assert isinstance(agent["tools"], list)
        assert "Read" in agent["tools"]
        assert "Write" in agent["tools"]
```

### Commands to Run
```bash
# Run route tests
uv run pytest tests/test_routes.py -v

# Run all tests
uv run pytest tests/ -v

# Manual API testing (optional)
uv run claude-subagent-editor &
sleep 2
curl http://127.0.0.1:8765/api/health
curl -X POST http://127.0.0.1:8765/api/project/scan \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/your/project"}'
pkill -f "claude-subagent-editor"
```

### Expected Output
```
tests/test_routes.py::TestHealthEndpoint::test_health_check PASSED
tests/test_routes.py::TestProjectScan::test_scan_valid_project PASSED
tests/test_routes.py::TestProjectScan::test_scan_nonexistent_directory PASSED
tests/test_routes.py::TestProjectScan::test_scan_file_not_directory PASSED
tests/test_routes.py::TestProjectScan::test_scan_project_without_agents PASSED
tests/test_routes.py::TestProjectAgents::test_list_agents_no_project PASSED
tests/test_routes.py::TestProjectAgents::test_list_agents_after_scan PASSED
tests/test_routes.py::TestGetAgent::test_get_agent_no_project PASSED
tests/test_routes.py::TestGetAgent::test_get_agent_success PASSED
tests/test_routes.py::TestGetAgent::test_get_agent_not_found PASSED
tests/test_routes.py::TestGetAgent::test_get_agent_path_traversal PASSED
tests/test_routes.py::TestAgentData::test_agent_has_all_fields PASSED
tests/test_routes.py::TestAgentData::test_agent_tools_as_list PASSED
```

### Commit Message
```
feat: add FastAPI REST endpoints for agent management

- Add /api/health, /api/project/scan, /api/project/agents, /api/agent/{filename}
- Add MCP server discovery from .mcp.json files
- Add CORS middleware for development
- Add path traversal protection
- Full test coverage for all endpoints
```

---

## Task 5: React Scaffold

### Objective
Create the React frontend with Vite, TypeScript, shadcn/ui configuration, and design tokens.

### Files to Create

#### `frontend/package.json`
```json
{
  "name": "claude-subagent-editor-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0",
    "class-variance-authority": "^0.7.0",
    "lucide-react": "^0.469.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.18",
    "@types/react-dom": "^18.3.5",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.17",
    "typescript": "^5.7.2",
    "vite": "^6.0.7"
  }
}
```

#### `frontend/vite.config.ts`
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
```

#### `frontend/tsconfig.json`
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

#### `frontend/tsconfig.node.json`
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

#### `frontend/tailwind.config.ts`
```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--color-bg)',
        'background-elevated': 'var(--color-bg-elevated)',
        'background-hover': 'var(--color-bg-hover)',
        border: 'var(--color-border)',
        'border-subtle': 'var(--color-border-subtle)',
        foreground: 'var(--color-text-primary)',
        'foreground-secondary': 'var(--color-text-secondary)',
        'foreground-muted': 'var(--color-text-muted)',
        tool: 'var(--color-tool)',
        'tool-bg': 'var(--color-tool-bg)',
        mcp: 'var(--color-mcp)',
        'mcp-bg': 'var(--color-mcp-bg)',
        skill: 'var(--color-skill)',
        'skill-bg': 'var(--color-skill-bg)',
        opus: 'var(--color-opus)',
        sonnet: 'var(--color-sonnet)',
        haiku: 'var(--color-haiku)',
      },
      fontFamily: {
        mono: ['var(--font-mono)'],
        sans: ['var(--font-sans)'],
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
      },
    },
  },
  plugins: [],
}

export default config
```

#### `frontend/postcss.config.js`
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

#### `frontend/components.json`
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/index.css",
    "baseColor": "zinc",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "registries": {
    "@aceternity": "https://ui.aceternity.com/registry/{name}.json",
    "@bundui": "https://bundui.io/r/{name}.json"
  }
}
```

#### `frontend/index.html`
```html
<!DOCTYPE html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Claude Subagent Editor</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

#### `frontend/src/tokens.css`
```css
:root {
  /* Colors - Neutral palette with accent */
  --color-bg: #0a0a0a;
  --color-bg-elevated: #141414;
  --color-bg-hover: #1a1a1a;
  --color-border: #262626;
  --color-border-subtle: #1a1a1a;

  --color-text-primary: #fafafa;
  --color-text-secondary: #a1a1aa;
  --color-text-muted: #71717a;

  /* Accent colors for resource types */
  --color-tool: #3b82f6;        /* Blue - base tools */
  --color-tool-bg: #3b82f610;
  --color-mcp: #a855f7;         /* Purple - MCP servers */
  --color-mcp-bg: #a855f710;
  --color-skill: #22c55e;       /* Green - skills */
  --color-skill-bg: #22c55e10;

  /* Model indicators */
  --color-opus: #f97316;        /* Orange */
  --color-sonnet: #06b6d4;      /* Cyan */
  --color-haiku: #84cc16;       /* Lime */

  /* Spacing scale */
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-12: 3rem;     /* 48px */

  /* Typography */
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --font-sans: 'Inter', system-ui, sans-serif;

  --text-xs: 0.75rem;   /* 12px */
  --text-sm: 0.875rem;  /* 14px */
  --text-base: 1rem;    /* 16px */
  --text-lg: 1.125rem;  /* 18px */
  --text-xl: 1.25rem;   /* 20px */

  /* Radii */
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.4);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.5);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.6);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-base: 200ms ease;
  --transition-slow: 300ms ease;

  /* Z-index layers */
  --z-base: 0;
  --z-dropdown: 100;
  --z-modal: 200;
  --z-toast: 300;
}
```

#### `frontend/src/index.css`
```css
@import './tokens.css';

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  * {
    @apply border-border;
  }

  body {
    @apply bg-background text-foreground font-sans antialiased;
    font-feature-settings: "rlig" 1, "calt" 1;
  }

  code, pre, .font-mono {
    font-family: var(--font-mono);
  }
}
```

#### `frontend/src/lib/utils.ts`
```typescript
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

#### `frontend/src/types/index.ts`
```typescript
export type ModelType = 'opus' | 'sonnet' | 'haiku'

export interface AgentConfig {
  filename: string
  name: string
  description: string
  model: ModelType
  tools: string[]
  skills: string[]
  nickname: string | null
  body: string
}

export interface ProjectScanResponse {
  path: string
  agents: AgentConfig[]
  mcp_servers: string[]
  agent_count: number
}

export interface HealthResponse {
  status: 'healthy'
  version: string
}
```

#### `frontend/src/App.tsx`
```typescript
import { useEffect, useState } from 'react'
import type { AgentConfig, ProjectScanResponse } from '@/types'

function App() {
  const [projectPath, setProjectPath] = useState<string>('')
  const [agents, setAgents] = useState<AgentConfig[]>([])
  const [mcpServers, setMcpServers] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const scanProject = async () => {
    if (!projectPath.trim()) return

    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/project/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: projectPath }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to scan project')
      }

      const data: ProjectScanResponse = await response.json()
      setAgents(data.agents)
      setMcpServers(data.mcp_servers)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setIsLoading(false)
    }
  }

  const getModelColor = (model: string) => {
    switch (model) {
      case 'opus': return 'text-opus'
      case 'sonnet': return 'text-sonnet'
      case 'haiku': return 'text-haiku'
      default: return 'text-foreground-muted'
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-foreground">
            Claude Subagent Editor
          </h1>
          <div className="flex items-center gap-4">
            <input
              type="text"
              value={projectPath}
              onChange={(e) => setProjectPath(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && scanProject()}
              placeholder="Enter project path..."
              className="w-80 rounded-md border border-border bg-background-elevated px-3 py-2 text-sm text-foreground placeholder:text-foreground-muted focus:border-tool focus:outline-none"
            />
            <button
              onClick={scanProject}
              disabled={isLoading || !projectPath.trim()}
              className="rounded-md bg-tool px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-tool/90 disabled:opacity-50"
            >
              {isLoading ? 'Scanning...' : 'Scan'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex">
        {/* Sidebar - Resources */}
        <aside className="w-64 border-r border-border p-4">
          <h2 className="mb-4 text-sm font-medium text-foreground-secondary">
            Resources
          </h2>

          {/* Base Tools */}
          <div className="mb-4">
            <h3 className="mb-2 text-xs font-medium text-foreground-muted">
              Base Tools
            </h3>
            <div className="flex flex-wrap gap-1">
              {['Read', 'Write', 'Edit', 'Bash', 'Glob', 'Grep'].map((tool) => (
                <span
                  key={tool}
                  className="rounded-full bg-tool-bg px-2 py-1 text-xs text-tool"
                >
                  {tool}
                </span>
              ))}
            </div>
          </div>

          {/* MCP Servers */}
          {mcpServers.length > 0 && (
            <div className="mb-4">
              <h3 className="mb-2 text-xs font-medium text-foreground-muted">
                MCP Servers
              </h3>
              <div className="flex flex-wrap gap-1">
                {mcpServers.map((server) => (
                  <span
                    key={server}
                    className="rounded-full bg-mcp-bg px-2 py-1 text-xs text-mcp"
                  >
                    {server}
                  </span>
                ))}
              </div>
            </div>
          )}
        </aside>

        {/* Agent Grid */}
        <section className="flex-1 p-6">
          {error && (
            <div className="mb-4 rounded-md bg-red-500/10 p-4 text-red-400">
              {error}
            </div>
          )}

          {agents.length === 0 ? (
            <div className="flex h-64 items-center justify-center text-foreground-muted">
              {projectPath
                ? 'No agents found. Check if .claude/agents/ exists.'
                : 'Enter a project path to scan for agents.'}
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {agents.map((agent) => (
                <div
                  key={agent.filename}
                  className="rounded-lg border border-border bg-background-elevated p-4 transition-colors hover:border-border/80"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <h3 className="font-medium text-foreground">{agent.name}</h3>
                    <span className={`text-xs font-medium ${getModelColor(agent.model)}`}>
                      {agent.model}
                    </span>
                  </div>

                  {agent.nickname && (
                    <p className="mb-2 text-sm text-foreground-muted">
                      "{agent.nickname}"
                    </p>
                  )}

                  <p className="mb-3 text-sm text-foreground-secondary line-clamp-2">
                    {agent.description}
                  </p>

                  {agent.tools.length > 0 && (
                    <div className="mb-2">
                      <p className="mb-1 text-xs text-foreground-muted">Tools:</p>
                      <div className="flex flex-wrap gap-1">
                        {agent.tools.slice(0, 5).map((tool) => (
                          <span
                            key={tool}
                            className="rounded bg-tool-bg px-1.5 py-0.5 text-xs text-tool"
                          >
                            {tool}
                          </span>
                        ))}
                        {agent.tools.length > 5 && (
                          <span className="text-xs text-foreground-muted">
                            +{agent.tools.length - 5}
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {agent.skills.length > 0 && (
                    <div>
                      <p className="mb-1 text-xs text-foreground-muted">Skills:</p>
                      <div className="flex flex-wrap gap-1">
                        {agent.skills.map((skill) => (
                          <span
                            key={skill}
                            className="rounded bg-skill-bg px-1.5 py-0.5 text-xs text-skill"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
```

#### `frontend/src/main.tsx`
```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

#### `frontend/src/vite-env.d.ts`
```typescript
/// <reference types="vite/client" />
```

### Directory Structure After Task 5
```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.node.json
├── tailwind.config.ts
├── postcss.config.js
├── components.json
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── tokens.css
    ├── vite-env.d.ts
    ├── lib/
    │   └── utils.ts
    └── types/
        └── index.ts
```

### Commands to Run
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server (in separate terminal)
npm run dev

# Build for production
npm run build

# Copy built files to Python package static directory
mkdir -p ../src/claude_subagent_editor/static
cp -r dist/* ../src/claude_subagent_editor/static/
```

### Expected Output
After `npm run build`:
```
vite v6.0.7 building for production...
✓ 32 modules transformed.
dist/index.html                   0.48 kB
dist/assets/index-[hash].css      2.15 kB
dist/assets/index-[hash].js      45.23 kB
✓ built in 1.23s
```

### Commit Message
```
feat: add React frontend scaffold with Vite and design tokens

- Create Vite + React + TypeScript project structure
- Configure Tailwind CSS with custom design tokens from spec
- Add shadcn/ui components.json with aceternity/bundui registries
- Create basic App.tsx with project scanning and agent grid
- Set up API proxy for development mode
```

---

## Task 6: Integration

### Objective
Integrate the React build with FastAPI and verify full stack works together.

### Files to Update

#### `src/claude_subagent_editor/main.py` (final version)
```python
"""FastAPI application for Claude Subagent Editor."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from claude_subagent_editor.api.routes import router

app = FastAPI(
    title="Claude Subagent Editor",
    description="Visual editor for Claude Code agent configurations",
    version="0.1.0",
)

# CORS configuration for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:8765",
        "http://127.0.0.1:8765",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Static file serving
static_dir = Path(__file__).parent / "static"


@app.get("/", response_class=HTMLResponse)
async def serve_spa():
    """Serve the React SPA."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse(
        content="""
        <html>
        <head><title>Claude Subagent Editor</title></head>
        <body style="background:#0a0a0a;color:#fafafa;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
            <div style="text-align:center">
                <h1>Claude Subagent Editor</h1>
                <p style="color:#71717a">Frontend not built. Run: cd frontend && npm run build</p>
            </div>
        </body>
        </html>
        """,
        status_code=200,
    )


# Mount static assets if directory exists
if static_dir.exists():
    # Serve static assets (JS, CSS, etc.)
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")
```

#### `pyproject.toml` (update to include static files)
```toml
[project]
name = "claude-subagent-editor"
version = "0.1.0"
description = "Web-based editor for Claude Code subagent YAML configuration files"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "ruamel.yaml>=0.18.0",
    "pydantic>=2.5.0",
    "watchfiles>=0.21.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.26.0",
]

[project.scripts]
claude-subagent-editor = "claude_subagent_editor.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/claude_subagent_editor"]

[tool.hatch.build.targets.wheel.sources]
"src" = ""

[tool.hatch.build]
include = [
    "src/claude_subagent_editor/**/*.py",
    "src/claude_subagent_editor/static/**/*",
]
```

#### `scripts/build.sh` (convenience script)
```bash
#!/bin/bash
# Build script for Claude Subagent Editor

set -e

echo "Building React frontend..."
cd frontend
npm install
npm run build

echo "Copying to Python package..."
rm -rf ../src/claude_subagent_editor/static
mkdir -p ../src/claude_subagent_editor/static
cp -r dist/* ../src/claude_subagent_editor/static/

echo "Build complete!"
echo "Run: uv run claude-subagent-editor"
```

### Commands to Run
```bash
# Build frontend and copy to static
chmod +x scripts/build.sh
./scripts/build.sh

# Run all tests
uv run pytest tests/ -v

# Start the integrated server
uv run claude-subagent-editor

# In another terminal, test the endpoints
curl http://127.0.0.1:8765/api/health

# Open browser to http://127.0.0.1:8765
```

### Expected Output
When visiting `http://127.0.0.1:8765`:
- React app loads showing "Claude Subagent Editor" header
- Input field for project path
- Sidebar with base tools listed
- Empty agent grid with placeholder text

When scanning a project with agents:
- Agent cards appear in grid
- Tools/skills shown with colored chips
- Model indicator (opus/sonnet/haiku) with appropriate color

### Integration Test (Manual)
```bash
# Create a test project with agent
mkdir -p /tmp/test-project/.claude/agents
cat > /tmp/test-project/.claude/agents/test-agent.md << 'EOF'
---
name: test-agent
description: A test agent for integration testing
model: opus
tools:
  - Read
  - Write
nickname: Testy
---

# Test Agent

This is a test agent.
EOF

# Start server
uv run claude-subagent-editor &

# Wait for startup
sleep 2

# Test API
curl -s http://127.0.0.1:8765/api/health | jq .
curl -s -X POST http://127.0.0.1:8765/api/project/scan \
  -H "Content-Type: application/json" \
  -d '{"path": "/tmp/test-project"}' | jq .

# Open in browser
open http://127.0.0.1:8765

# Cleanup
pkill -f "claude-subagent-editor"
rm -rf /tmp/test-project
```

### Commit Message
```
feat: integrate React frontend with FastAPI backend

- Configure FastAPI to serve built React assets
- Add SPA fallback for index.html
- Update pyproject.toml to include static files in wheel
- Add build.sh script for one-command builds
- Full stack integration complete
```

---

## Final Verification Checklist

After completing all tasks:

- [ ] `uv run claude-subagent-editor` starts server on port 8765
- [ ] `GET /api/health` returns `{"status": "healthy", "version": "0.1.0"}`
- [ ] `POST /api/project/scan` discovers agents and MCP servers
- [ ] `GET /api/project/agents` lists all agents
- [ ] `GET /api/agent/{filename}` returns single agent details
- [ ] React app loads at `http://127.0.0.1:8765`
- [ ] Project scan UI works and displays agent cards
- [ ] All tests pass: `uv run pytest tests/ -v`

## Project Structure After Phase 1

```
claude_subagent_editor/
├── pyproject.toml
├── scripts/
│   └── build.sh
├── src/
│   └── claude_subagent_editor/
│       ├── __init__.py
│       ├── __main__.py
│       ├── main.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── routes.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── schemas.py
│       ├── services/
│       │   ├── __init__.py
│       │   └── agent_parser.py
│       └── static/
│           ├── index.html
│           └── assets/
│               ├── index-[hash].js
│               └── index-[hash].css
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── components.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── tokens.css
│       ├── lib/
│       │   └── utils.ts
│       └── types/
│           └── index.ts
└── tests/
    ├── __init__.py
    ├── test_agent_parser.py
    ├── test_schemas.py
    └── test_routes.py
```

---

## Summary

This Phase 1 implementation plan provides:

1. **Python project setup** with uv and FastAPI entry point
2. **Agent parser service** using ruamel.yaml for YAML frontmatter preservation
3. **Pydantic models** for strict API validation
4. **FastAPI application** with health, scan, list, and get endpoints
5. **React scaffold** with Vite, TypeScript, Tailwind, and design tokens
6. **Full integration** of frontend and backend

Each task has exact file paths, complete code, test coverage, commands, and commit messages for TDD-style implementation.
