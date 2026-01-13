# Claude Subagent Editor

A web-based GUI for editing Claude Code subagent configuration files. Manage your AI agents visually with drag-and-drop simplicity.

![Screenshot](screenshot.png)

## Features

- **Project Scanner** - Automatically discovers `.claude/agents/*.md` files in your projects
- **Visual YAML Editor** - Edit agent frontmatter (name, description, model, tools, skills) through an intuitive interface
- **Drag-and-Drop Assignment** - Easily assign tools, skills, and MCP servers to agents
- **Three-Tab System**
  - **Tools** - Base Claude tools available to agents
  - **Skills** - Discovered from `~/.claude/plugins`
  - **MCP** - Servers discovered via `claude mcp list` (with wildcard format support)
- **Multi-Project Support** - Manage agents across multiple projects with persistence

## Installation

```bash
uvx claude-subagent-editor
```

## Usage

1. Open [http://127.0.0.1:8765](http://127.0.0.1:8765) in your browser
2. Add a project path using the interface
3. Click on a project to view its agents
4. Click **Edit** to modify an agent's configuration
5. Drag tools, skills, or MCP servers to assign them to the agent
6. Click **Save** to persist your changes

## Tech Stack

- **Backend:** FastAPI (Python)
- **Frontend:** React
- **Distribution:** uvx

## Requirements

- Python 3.10+
- Claude Code CLI (for MCP server discovery)

## How It Works

The editor reads and writes to `.claude/agents/*.md` files in your projects. These Markdown files contain YAML frontmatter that defines agent properties:

```yaml
---
name: my-agent
description: A helpful assistant
model: claude-sonnet-4-20250514
tools:
  - Read
  - Write
  - Bash
allowed_mcp_servers:
  - filesystem
---

Agent instructions go here...
```

## Links

- **GitHub:** [https://github.com/Hearmeman24/claude-subagent-editor](https://github.com/Hearmeman24/claude-subagent-editor)

## License

MIT

---

Created by [Hearmeman24](https://github.com/Hearmeman24)
