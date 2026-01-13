"""API routes for Claude Subagent Editor."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from claude_subagent_editor import __version__
from claude_subagent_editor.models.schemas import (
    AgentConfig,
    AgentListResponse,
    AgentResponse,
    AgentUpdateRequest,
    GlobalResourcesResponse,
    HealthResponse,
    MCPServerInfo,
    MCPServerWithTools,
    MCPToolInfo,
    MCPToolsResponse,
    ProjectScanRequest,
    ProjectScanResponse,
    SkillInfo,
)
from claude_subagent_editor.services.agent_parser import AgentParser
from claude_subagent_editor.services.discovery import ResourceDiscovery
from claude_subagent_editor.services.mcp_tool_discovery import (
    MCPToolDiscovery,
    MCPServerWithTools as MCPServerWithToolsDataclass,
    MCPToolInfo as MCPToolInfoDataclass,
)

router = APIRouter()

# Global state
_current_project: Path | None = None
_parser = AgentParser()
_discovery = ResourceDiscovery()
_tool_discovery = MCPToolDiscovery()

# Logger
logger = logging.getLogger(__name__)


def _convert_dataclass_to_pydantic_server(
    dc_server: MCPServerWithToolsDataclass,
) -> MCPServerWithTools:
    """Convert dataclass MCPServerWithTools to Pydantic model.

    Args:
        dc_server: Dataclass instance from discovery service.

    Returns:
        MCPServerWithTools: Pydantic model instance.
    """
    tools = []
    if dc_server.tools:
        tools = [
            MCPToolInfo(
                name=tool.name,
                full_name=tool.full_name,
                description=tool.description,
            )
            for tool in dc_server.tools
        ]

    return MCPServerWithTools(
        name=dc_server.name,
        connected=dc_server.connected,
        error=dc_server.error,
        tools=tools,
    )


def _get_project_path() -> Path:
    """Get current project path or raise HTTPException.

    Returns:
        Path: The current project path.

    Raises:
        HTTPException: If no project has been scanned.
    """
    if _current_project is None:
        raise HTTPException(
            status_code=400,
            detail="No project scanned. Please scan a project first.",
        )
    return _current_project


def _get_agents_dir(project_path: Path) -> Path:
    """Get the agents directory for a project.

    Args:
        project_path: The project root directory.

    Returns:
        Path: The .claude/agents directory path.
    """
    return project_path / ".claude" / "agents"


def _parse_agent_file(file_path: Path) -> AgentConfig:
    """Parse an agent file and return AgentConfig.

    Args:
        file_path: Path to the agent file.

    Returns:
        AgentConfig: Parsed agent configuration.

    Raises:
        ValueError: If the file cannot be parsed.
    """
    parsed = _parser.parse_file(file_path)
    return AgentConfig(
        filename=parsed.filename,
        name=parsed.name,
        description=parsed.description,
        model=parsed.model,
        tools=parsed.tools,
        skills=parsed.skills,
        disallowed_tools=parsed.disallowed_tools,
        nickname=parsed.nickname,
        body=parsed.body,
    )


def _discover_mcp_servers(project_path: Path) -> list[str]:
    """Discover MCP servers from .mcp.json files.

    Checks both the project directory and ~/.claude.json.

    Args:
        project_path: The project root directory.

    Returns:
        list[str]: List of MCP server names.
    """
    servers: set[str] = set()

    # Check project .mcp.json
    project_mcp = project_path / ".mcp.json"
    if project_mcp.exists():
        try:
            data = json.loads(project_mcp.read_text(encoding="utf-8"))
            if "mcpServers" in data:
                servers.update(data["mcpServers"].keys())
        except (json.JSONDecodeError, KeyError):
            pass

    # Check global ~/.claude.json
    global_config = Path.home() / ".claude.json"
    if global_config.exists():
        try:
            data = json.loads(global_config.read_text(encoding="utf-8"))
            if "mcpServers" in data:
                servers.update(data["mcpServers"].keys())
        except (json.JSONDecodeError, KeyError):
            pass

    return sorted(servers)


@router.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        HealthResponse: Health status and version information.
    """
    return HealthResponse(version=__version__)


@router.post("/api/project/scan", response_model=ProjectScanResponse)
async def scan_project(request: ProjectScanRequest) -> ProjectScanResponse:
    """Scan a project directory for agents.

    Args:
        request: Project scan request with path.

    Returns:
        ProjectScanResponse: Scanned project information.

    Raises:
        HTTPException: If the path does not exist or is not a directory.
    """
    global _current_project

    project_path = Path(request.path)

    # Validate path exists
    if not project_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Path does not exist: {request.path}",
        )

    # Validate path is a directory
    if not project_path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a directory: {request.path}",
        )

    # Set current project
    _current_project = project_path

    # Find and parse agents
    agents: list[AgentConfig] = []
    agents_dir = _get_agents_dir(project_path)

    if agents_dir.exists() and agents_dir.is_dir():
        for agent_file in sorted(agents_dir.glob("*.md")):
            try:
                agent_config = _parse_agent_file(agent_file)
                agents.append(agent_config)
            except ValueError as e:
                logger.warning(f"Skipping invalid agent file {agent_file}: {e}")

    # Discover MCP servers from .mcp.json files
    mcp_servers = _discover_mcp_servers(project_path)

    # Discover global skills
    discovered_skills = _discovery.discover_skills()
    skills = [
        SkillInfo(name=s.name, path=s.path, description=s.description)
        for s in discovered_skills
    ]

    # Discover connected MCP servers via claude mcp list
    discovered_servers = _discovery.discover_mcp_servers()
    connected_mcp_servers = [
        MCPServerInfo(
            name=s.name,
            command=s.command,
            url=s.url,
            connected=s.connected,
        )
        for s in discovered_servers
    ]

    return ProjectScanResponse(
        path=str(project_path),
        agents=agents,
        mcp_servers=mcp_servers,
        agent_count=len(agents),
        skills=skills,
        connected_mcp_servers=connected_mcp_servers,
    )


@router.get("/api/project/agents", response_model=AgentListResponse)
async def list_agents() -> AgentListResponse:
    """List all agents in the current project.

    Returns:
        AgentListResponse: List of agents.

    Raises:
        HTTPException: If no project has been scanned.
    """
    project_path = _get_project_path()

    # Find and parse agents
    agents: list[AgentConfig] = []
    agents_dir = _get_agents_dir(project_path)

    if agents_dir.exists() and agents_dir.is_dir():
        for agent_file in sorted(agents_dir.glob("*.md")):
            try:
                agent_config = _parse_agent_file(agent_file)
                agents.append(agent_config)
            except ValueError as e:
                logger.warning(f"Skipping invalid agent file {agent_file}: {e}")

    return AgentListResponse(agents=agents, count=len(agents))


@router.get("/api/agent/{filename:path}", response_model=AgentResponse)
async def get_agent(filename: str) -> AgentResponse:
    """Get a specific agent by filename.

    Args:
        filename: The agent filename.

    Returns:
        AgentResponse: The agent configuration.

    Raises:
        HTTPException: If no project has been scanned, filename is invalid,
                      or agent is not found.
    """
    project_path = _get_project_path()

    # Path traversal protection - check for any path separators or relative paths
    if (
        "/" in filename
        or "\\" in filename
        or ".." in filename
        or filename in (".", "..")
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid filename: {filename}",
        )

    # Get agent file
    agents_dir = _get_agents_dir(project_path)
    agent_file = agents_dir / filename

    # Check if file exists
    if not agent_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Agent not found: {filename}",
        )

    # Check if it's a file (not a directory)
    if not agent_file.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"Invalid filename: {filename}",
        )

    # Parse and return agent
    try:
        agent_config = _parse_agent_file(agent_file)
        return AgentResponse(agent=agent_config)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse agent: {str(e)}",
        )


@router.put("/api/agent/{filename:path}", response_model=AgentResponse)
async def update_agent(filename: str, request: AgentUpdateRequest) -> AgentResponse:
    """Update an agent file.

    Args:
        filename: The agent filename.
        request: The updated agent data.

    Returns:
        AgentResponse: The updated agent configuration.

    Raises:
        HTTPException: If no project has been scanned, filename is invalid,
                      or agent cannot be updated.
    """
    project_path = _get_project_path()

    # Path traversal protection - same checks as GET endpoint
    if (
        "/" in filename
        or "\\" in filename
        or ".." in filename
        or filename in (".", "..")
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid filename: {filename}",
        )

    # Get agent file path
    agents_dir = _get_agents_dir(project_path)
    agent_file = agents_dir / filename

    # Check if file exists
    if not agent_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Agent not found: {filename}",
        )

    # Check if it's a file (not a directory)
    if not agent_file.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"Invalid filename: {filename}",
        )

    # Create ParsedAgent from request
    from claude_subagent_editor.services.agent_parser import ParsedAgent

    parsed_agent = ParsedAgent(
        filename=filename,
        name=request.name,
        description=request.description,
        model=request.model.value,
        tools=request.tools,
        skills=request.skills,
        disallowed_tools=request.disallowed_tools,
        body=request.body,
    )

    # Serialize to markdown with YAML frontmatter
    try:
        content = _parser.serialize(parsed_agent)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to serialize agent: {str(e)}",
        )

    # Write the file
    try:
        agent_file.write_text(content, encoding="utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to write agent file: {str(e)}",
        )

    # Parse and return the updated agent
    try:
        agent_config = _parse_agent_file(agent_file)
        return AgentResponse(agent=agent_config)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse updated agent: {str(e)}",
        )


@router.get("/api/resources/global", response_model=GlobalResourcesResponse)
async def get_global_resources() -> GlobalResourcesResponse:
    """Get globally available resources (skills and MCP servers).

    This endpoint discovers:
    - Skills from ~/.claude/plugins recursively
    - MCP servers via 'claude mcp list' command

    Returns:
        GlobalResourcesResponse: Discovered global resources.
    """
    # Discover skills
    discovered_skills = _discovery.discover_skills()
    skills = [
        SkillInfo(name=s.name, path=s.path, description=s.description)
        for s in discovered_skills
    ]

    # Discover MCP servers
    discovered_servers = _discovery.discover_mcp_servers()
    mcp_servers = [
        MCPServerInfo(
            name=s.name,
            command=s.command,
            url=s.url,
            connected=s.connected,
        )
        for s in discovered_servers
    ]

    return GlobalResourcesResponse(skills=skills, mcp_servers=mcp_servers)


@router.get("/api/mcp/tools", response_model=MCPToolsResponse)
async def get_mcp_tools() -> MCPToolsResponse:
    """Get all MCP tools from all configured servers.

    This endpoint queries MCP servers from both project and global .mcp.json files,
    connects to each server, and retrieves their available tools.

    Tool names follow the convention: mcp__server-name__tool-name
    For example: mcp__playwright__browser_click

    Returns:
        MCPToolsResponse: All discovered tools grouped by server.
    """
    all_servers: list[MCPServerWithToolsDataclass] = []

    # Check project .mcp.json if available
    if _current_project is not None:
        project_mcp = _current_project / ".mcp.json"
        if project_mcp.exists():
            try:
                servers = await _tool_discovery.discover_all_tools(project_mcp)
                all_servers.extend(servers)
                logger.debug("Discovered %d servers from project .mcp.json", len(servers))
            except Exception as e:
                logger.warning("Error discovering tools from project .mcp.json: %s", e)

    # Check global ~/.claude.json
    global_config = Path.home() / ".claude.json"
    if global_config.exists():
        try:
            servers = await _tool_discovery.discover_all_tools(global_config)
            # Only add servers that aren't already in all_servers
            existing_names = {s.name for s in all_servers}
            for server in servers:
                if server.name not in existing_names:
                    all_servers.append(server)
            logger.debug("Discovered %d servers from global config", len(servers))
        except Exception as e:
            logger.warning("Error discovering tools from global config: %s", e)

    # Also check .mcp.json in the working directory (for the spec requirement)
    cwd_mcp = Path.cwd() / ".mcp.json"
    if cwd_mcp.exists() and cwd_mcp != global_config:
        try:
            servers = await _tool_discovery.discover_all_tools(cwd_mcp)
            existing_names = {s.name for s in all_servers}
            for server in servers:
                if server.name not in existing_names:
                    all_servers.append(server)
            logger.debug("Discovered %d servers from cwd .mcp.json", len(servers))
        except Exception as e:
            logger.warning("Error discovering tools from cwd .mcp.json: %s", e)

    # Convert dataclass instances to Pydantic models
    pydantic_servers = [_convert_dataclass_to_pydantic_server(s) for s in all_servers]

    return MCPToolsResponse(servers=pydantic_servers)
