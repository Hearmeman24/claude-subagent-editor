"""Tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError


class TestModelType:
    """Test ModelType enum."""

    def test_all_model_types(self):
        """Test all valid model types."""
        from claude_subagent_editor.models.schemas import ModelType

        assert ModelType.OPUS == "opus"
        assert ModelType.SONNET == "sonnet"
        assert ModelType.HAIKU == "haiku"


class TestToolConfig:
    """Test ToolConfig schema."""

    def test_base_tool(self):
        """Test base tool configuration."""
        from claude_subagent_editor.models.schemas import ToolConfig, ToolType

        tool = ToolConfig(
            name="read_file",
            tool_type=ToolType.BASE,
            description="Read files"
        )

        assert tool.name == "read_file"
        assert tool.tool_type == ToolType.BASE
        assert tool.mcp_server is None
        assert tool.description == "Read files"

    def test_mcp_tool(self):
        """Test MCP tool configuration."""
        from claude_subagent_editor.models.schemas import ToolConfig, ToolType

        tool = ToolConfig(
            name="git_status",
            tool_type=ToolType.MCP,
            mcp_server="git-server",
            description="Git operations"
        )

        assert tool.name == "git_status"
        assert tool.tool_type == ToolType.MCP
        assert tool.mcp_server == "git-server"
        assert tool.description == "Git operations"


class TestSkillConfig:
    """Test SkillConfig schema."""

    def test_basic_config(self):
        """Test basic skill configuration."""
        from claude_subagent_editor.models.schemas import SkillConfig

        skill = SkillConfig(
            name="python",
            description="Python expertise",
            path="/skills/python.md"
        )

        assert skill.name == "python"
        assert skill.description == "Python expertise"
        assert skill.path == "/skills/python.md"


class TestAgentConfig:
    """Test AgentConfig schema."""

    def test_valid_config(self):
        """Test valid agent configuration."""
        from claude_subagent_editor.models.schemas import AgentConfig, ModelType

        config = AgentConfig(
            filename="python-backend.yaml",
            name="python-backend-supervisor",
            description="Python backend development",
            model=ModelType.OPUS,
            tools=["read", "write"],
            skills=["python", "fastapi"],
            nickname="Tessa",
            body="Expert Python developer"
        )

        assert config.filename == "python-backend.yaml"
        assert config.name == "python-backend-supervisor"
        assert config.description == "Python backend development"
        assert config.model == ModelType.OPUS
        assert config.tools == ["read", "write"]
        assert config.skills == ["python", "fastapi"]
        assert config.nickname == "Tessa"
        assert config.body == "Expert Python developer"

    def test_defaults(self):
        """Test agent configuration with defaults."""
        from claude_subagent_editor.models.schemas import AgentConfig, ModelType

        config = AgentConfig(
            filename="test.yaml",
            name="test-agent",
            description="Test agent",
            model=ModelType.SONNET
        )

        assert config.tools == []
        assert config.skills == []
        assert config.nickname is None
        assert config.body == ""

    def test_model_string_coercion(self):
        """Test model type can be coerced from string."""
        from claude_subagent_editor.models.schemas import AgentConfig, ModelType

        config = AgentConfig(
            filename="test.yaml",
            name="test-agent",
            description="Test agent",
            model="opus"  # String should be coerced to ModelType
        )

        assert config.model == ModelType.OPUS

    def test_invalid_model(self):
        """Test invalid model type raises validation error."""
        from claude_subagent_editor.models.schemas import AgentConfig

        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(
                filename="test.yaml",
                name="test-agent",
                description="Test agent",
                model="invalid-model"
            )

        assert "model" in str(exc_info.value)

    def test_missing_required(self):
        """Test missing required fields raises validation error."""
        from claude_subagent_editor.models.schemas import AgentConfig

        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(
                filename="test.yaml",
                name="test-agent"
                # Missing description and model
            )

        errors = exc_info.value.errors()
        missing_fields = {error["loc"][0] for error in errors}
        assert "description" in missing_fields
        assert "model" in missing_fields

    def test_extra_fields_forbidden(self):
        """Test extra fields are forbidden."""
        from claude_subagent_editor.models.schemas import AgentConfig, ModelType

        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(
                filename="test.yaml",
                name="test-agent",
                description="Test agent",
                model=ModelType.SONNET,
                extra_field="not allowed"
            )

        assert "extra_field" in str(exc_info.value)


class TestHealthResponse:
    """Test HealthResponse schema."""

    def test_basic_response(self):
        """Test basic health response."""
        from claude_subagent_editor.models.schemas import HealthResponse

        response = HealthResponse(version="0.1.0")

        assert response.status == "healthy"
        assert response.version == "0.1.0"


class TestProjectScanRequest:
    """Test ProjectScanRequest schema."""

    def test_valid_request(self):
        """Test valid scan request."""
        from claude_subagent_editor.models.schemas import ProjectScanRequest

        request = ProjectScanRequest(path="/path/to/project")

        assert request.path == "/path/to/project"

    def test_missing_path(self):
        """Test missing path raises validation error."""
        from claude_subagent_editor.models.schemas import ProjectScanRequest

        with pytest.raises(ValidationError) as exc_info:
            ProjectScanRequest()

        assert "path" in str(exc_info.value)


class TestProjectScanResponse:
    """Test ProjectScanResponse schema."""

    def test_empty_response(self):
        """Test empty scan response."""
        from claude_subagent_editor.models.schemas import ProjectScanResponse

        response = ProjectScanResponse(
            path="/path/to/project",
            agent_count=0
        )

        assert response.path == "/path/to/project"
        assert response.agents == []
        assert response.mcp_servers == []
        assert response.agent_count == 0

    def test_with_agents(self):
        """Test scan response with agents."""
        from claude_subagent_editor.models.schemas import (
            AgentConfig,
            ModelType,
            ProjectScanResponse,
        )

        agent = AgentConfig(
            filename="test.yaml",
            name="test-agent",
            description="Test agent",
            model=ModelType.SONNET
        )

        response = ProjectScanResponse(
            path="/path/to/project",
            agents=[agent],
            mcp_servers=["git-server", "filesystem-server"],
            agent_count=1
        )

        assert response.path == "/path/to/project"
        assert len(response.agents) == 1
        assert response.agents[0].name == "test-agent"
        assert response.mcp_servers == ["git-server", "filesystem-server"]
        assert response.agent_count == 1


class TestAgentListResponse:
    """Test AgentListResponse schema."""

    def test_agent_list_response(self):
        """Test agent list response."""
        from claude_subagent_editor.models.schemas import (
            AgentConfig,
            AgentListResponse,
            ModelType,
        )

        agent1 = AgentConfig(
            filename="agent1.yaml",
            name="agent1",
            description="First agent",
            model=ModelType.OPUS
        )

        agent2 = AgentConfig(
            filename="agent2.yaml",
            name="agent2",
            description="Second agent",
            model=ModelType.SONNET
        )

        response = AgentListResponse(
            agents=[agent1, agent2],
            count=2
        )

        assert len(response.agents) == 2
        assert response.count == 2
        assert response.agents[0].name == "agent1"
        assert response.agents[1].name == "agent2"


class TestAgentResponse:
    """Test AgentResponse schema."""

    def test_single_agent_response(self):
        """Test single agent response."""
        from claude_subagent_editor.models.schemas import (
            AgentConfig,
            AgentResponse,
            ModelType,
        )

        agent = AgentConfig(
            filename="test.yaml",
            name="test-agent",
            description="Test agent",
            model=ModelType.HAIKU,
            nickname="Tester"
        )

        response = AgentResponse(agent=agent)

        assert response.agent.name == "test-agent"
        assert response.agent.model == ModelType.HAIKU
        assert response.agent.nickname == "Tester"
