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

    filename: str = Field(..., description="Filename of the agent")
    name: str = Field(..., description="Agent identifier")
    description: str = Field(..., description="What the agent does")
    model: ModelType = Field(..., description="Claude model to use")
    tools: list[str] = Field(default_factory=list, description="Assigned tools")
    skills: list[str] = Field(default_factory=list, description="Assigned skills")
    nickname: str | None = Field(None, description="Friendly name")
    body: str = Field(default="", description="Markdown body content")
    model_config = {"extra": "forbid"}


class HealthResponse(BaseModel):
    """Response for health check endpoint."""

    status: Literal["healthy"] = Field(default="healthy", description="Health status indicator")
    version: str = Field(..., description="Application version")
    model_config = {"extra": "forbid"}


class ProjectScanRequest(BaseModel):
    """Request to scan a project directory."""

    path: str = Field(..., description="Absolute path to project directory")
    model_config = {"extra": "forbid"}


class ProjectScanResponse(BaseModel):
    """Response from scanning a project."""

    path: str = Field(..., description="Scanned project path")
    agents: list[AgentConfig] = Field(default_factory=list, description="List of discovered agents")
    mcp_servers: list[str] = Field(default_factory=list, description="List of MCP server names")
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
