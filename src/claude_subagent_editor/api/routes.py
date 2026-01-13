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
    HealthResponse,
    ProjectScanRequest,
    ProjectScanResponse,
)
from claude_subagent_editor.services.agent_parser import AgentParser

router = APIRouter()

# Global state
_current_project: Path | None = None
_parser = AgentParser()

# Logger
logger = logging.getLogger(__name__)


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
        nickname=parsed.nickname,
        body=parsed.body,
    )


def _discover_mcp_servers(project_path: Path) -> list[str]:
    """Discover MCP servers from .mcp.json files.

    Checks both the project directory and ~/.claude/mcp.json.

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

    # Check ~/.claude/mcp.json
    home_mcp = Path.home() / ".claude" / "mcp.json"
    if home_mcp.exists():
        try:
            data = json.loads(home_mcp.read_text(encoding="utf-8"))
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
        for agent_file in sorted(agents_dir.glob("*.yaml")):
            try:
                agent_config = _parse_agent_file(agent_file)
                agents.append(agent_config)
            except ValueError as e:
                logger.warning(f"Skipping invalid agent file {agent_file}: {e}")

    # Discover MCP servers
    mcp_servers = _discover_mcp_servers(project_path)

    return ProjectScanResponse(
        path=str(project_path),
        agents=agents,
        mcp_servers=mcp_servers,
        agent_count=len(agents),
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
        for agent_file in sorted(agents_dir.glob("*.yaml")):
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
