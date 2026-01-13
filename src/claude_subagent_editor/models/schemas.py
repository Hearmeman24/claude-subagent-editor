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
    tools: list[str] | str = Field(default_factory=list, description="Assigned tools (list or '*' for all)")
    skills: list[str] = Field(default_factory=list, description="Assigned skills")
    disallowed_tools: list[str] = Field(default_factory=list, alias="disallowedTools", description="Tools to exclude when using '*'")
    nickname: str | None = Field(None, description="Friendly name")
    body: str = Field(default="", description="Markdown body content")
    model_config = {"extra": "forbid", "populate_by_name": True}


class HealthResponse(BaseModel):
    """Response for health check endpoint."""

    status: Literal["healthy"] = Field(default="healthy", description="Health status indicator")
    version: str = Field(..., description="Application version")
    model_config = {"extra": "forbid"}


class ProjectScanRequest(BaseModel):
    """Request to scan a project directory."""

    path: str = Field(..., description="Absolute path to project directory")
    model_config = {"extra": "forbid"}


class MCPServerInfo(BaseModel):
    """Information about a discovered MCP server."""

    name: str = Field(..., description="MCP server name")
    command: str | None = Field(None, description="Command to run server")
    url: str | None = Field(None, description="HTTP/HTTPS URL if server is remote")
    connected: bool = Field(..., description="Whether server is currently connected")
    model_config = {"extra": "forbid"}


class SkillInfo(BaseModel):
    """Information about a discovered skill."""

    name: str = Field(..., description="Skill name")
    path: str = Field(..., description="Path to skill file")
    description: str | None = Field(None, description="Skill description")
    model_config = {"extra": "forbid"}


class ProjectScanResponse(BaseModel):
    """Response from scanning a project."""

    path: str = Field(..., description="Scanned project path")
    agents: list[AgentConfig] = Field(default_factory=list, description="List of discovered agents")
    mcp_servers: list[str] = Field(
        default_factory=list, description="List of MCP server names from .mcp.json files"
    )
    agent_count: int = Field(..., description="Number of agents found")
    skills: list[SkillInfo] = Field(
        default_factory=list, description="Globally available skills from ~/.claude/plugins"
    )
    connected_mcp_servers: list[MCPServerInfo] = Field(
        default_factory=list, description="Connected MCP servers from 'claude mcp list'"
    )
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


class AgentUpdateRequest(BaseModel):
    """Request to update an agent."""

    name: str = Field(..., description="Agent identifier")
    description: str = Field(..., description="What the agent does")
    model: ModelType = Field(..., description="Claude model to use")
    tools: list[str] | str = Field(default_factory=list, description="Assigned tools (list or '*' for all)")
    skills: list[str] = Field(default_factory=list, description="Assigned skills")
    disallowed_tools: list[str] = Field(default_factory=list, alias="disallowedTools", description="Tools to exclude when using '*'")
    body: str = Field(default="", description="Markdown body content")
    model_config = {"extra": "forbid", "populate_by_name": True}


class MCPToolInfo(BaseModel):
    """Information about a discovered MCP tool."""

    name: str = Field(..., description="Original tool name from server")
    full_name: str = Field(..., description="Full name with prefix: mcp__server__tool")
    description: str | None = Field(None, description="Tool description")
    model_config = {"extra": "forbid"}


class MCPServerWithTools(BaseModel):
    """MCP server with its discovered tools."""

    name: str = Field(..., description="MCP server name")
    connected: bool = Field(..., description="Whether server is connected")
    error: str | None = Field(None, description="Error message if connection failed")
    tools: list[MCPToolInfo] = Field(default_factory=list, description="List of tools")
    model_config = {"extra": "forbid"}


class MCPToolsResponse(BaseModel):
    """Response containing MCP tools from all servers."""

    servers: list[MCPServerWithTools] = Field(
        default_factory=list, description="List of servers with their tools"
    )
    model_config = {"extra": "forbid"}


class GlobalResourcesResponse(BaseModel):
    """Response containing globally available resources."""

    skills: list[SkillInfo] = Field(default_factory=list, description="Discovered skills")
    mcp_servers: list[MCPServerInfo] = Field(
        default_factory=list, description="Discovered MCP servers"
    )
    model_config = {"extra": "forbid"}
