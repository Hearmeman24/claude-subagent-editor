# Claude Subagent Editor

A web-based GUI for editing Claude Code subagent configuration files. Manage your AI agents visually with drag-and-drop simplicity.

**Tested on macOS Tahoe and macOS Sequoia. No Windows support for now.**

## Screenshots

### Project Picker
![Project Picker](screenshots/project-picker.png)

### Agent Grid
![Agent Grid](screenshots/agent-grid.png)

### Edit Modal with Drag-and-Drop
![Edit Modal](screenshots/edit-modal.png)

## The Problem

Claude Code subagents are configured through markdown files with YAML frontmatter, located in `.claude/agents/`.
Managing tools, skills, and MCP servers for each agent means manually editing these files—keeping track of available options, avoiding typos, and remembering the exact syntax for MCP tool names like `mcp__playwright__browser_navigate`.

## The Solution

Claude Subagent Editor provides a visual interface that scans your projects, discovers available resources, and lets you configure agents through drag-and-drop. It automatically discovers base Claude tools, skills from `~/.claude/plugins`, and MCP servers from your configuration.

The editor uses a four-tab system for organizing resources: **Tools** (base Claude capabilities like Read, Write, Bash), **Skills** (your custom skills), **MCP** (with individual action selection per server), and **Disallowed** (tools to explicitly exclude). Drag items between Available and Assigned columns, or use "Add All" to quickly assign entire MCP servers.

Smart features include an "All Tools" mode that grants access to everything, automatic grouping of MCP tools by server in the overview, overflow handling for agents with many tools, and warnings when skills are assigned without the required Skill tool.

## Installation

```bash
git clone https://github.com/Hearmeman24/claude-subagent-editor
cd claude-subagent-editor
uv run claude-subagent-editor
```

Then open [http://127.0.0.1:8765](http://127.0.0.1:8765) in your browser.

## Tech Stack

- **Backend:** FastAPI (Python 3.10+)
- **Frontend:** React + TypeScript + Tailwind CSS

## Agent File Format

```yaml
---
name: my-agent
description: A helpful assistant
model: sonnet
tools:
  - Read
  - Write
  - mcp__playwright__browser_navigate
skills:
  - test-driven-development
disallowedTools:
  - Bash
---

Agent instructions in markdown...
```

## Links

- **GitHub:** [https://github.com/Hearmeman24/claude-subagent-editor](https://github.com/Hearmeman24/claude-subagent-editor)

## License

MIT

---

Created by [Hearmeman24](https://github.com/Hearmeman24)
