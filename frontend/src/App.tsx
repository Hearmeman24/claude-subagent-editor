import { useState } from 'react'
import { Folder, Plus } from 'lucide-react'
import type { AgentConfig, ProjectScanResponse, BaseTool, MCPServer, Skill } from '@/types'
import { cn } from '@/lib/utils'

const BASE_TOOLS: BaseTool[] = [
  { name: 'Read', category: 'file' },
  { name: 'Write', category: 'file' },
  { name: 'Edit', category: 'file' },
  { name: 'Glob', category: 'file' },
  { name: 'Grep', category: 'file' },
  { name: 'Bash', category: 'execution' },
  { name: 'Task', category: 'execution' },
  { name: 'LSP', category: 'code' },
  { name: 'WebFetch', category: 'web' },
  { name: 'WebSearch', category: 'web' },
  { name: 'NotebookEdit', category: 'notebook' },
  { name: 'TodoWrite', category: 'utility' },
  { name: 'AskUserQuestion', category: 'utility' },
]

function AgentCard({ agent }: { agent: AgentConfig }) {
  const modelColors = {
    opus: 'text-opus',
    sonnet: 'text-sonnet',
    haiku: 'text-haiku',
  }

  return (
    <div className="border border-border rounded-lg p-4 bg-background-elevated hover:bg-background-hover transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-mono text-base font-medium">{agent.name}</h3>
          {agent.nickname && (
            <p className="text-sm text-foreground-secondary">"{agent.nickname}"</p>
          )}
        </div>
        <span className={cn('text-xs font-medium uppercase', modelColors[agent.model])}>
          {agent.model}
        </span>
      </div>

      <p className="text-sm text-foreground-secondary mb-4 line-clamp-2">
        {agent.description}
      </p>

      {agent.tools && agent.tools.length > 0 && (
        <div className="mb-3">
          <div className="text-xs text-foreground-muted mb-1.5">Tools:</div>
          <div className="flex flex-wrap gap-1.5">
            {agent.tools.map((tool) => (
              <span
                key={tool}
                className="px-2 py-1 text-xs rounded bg-tool-bg text-tool border border-tool/20"
              >
                {tool}
              </span>
            ))}
          </div>
        </div>
      )}

      {agent.skills && agent.skills.length > 0 && (
        <div className="mb-3">
          <div className="text-xs text-foreground-muted mb-1.5">Skills:</div>
          <div className="flex flex-wrap gap-1.5">
            {agent.skills.map((skill) => (
              <span
                key={skill}
                className="px-2 py-1 text-xs rounded bg-skill-bg text-skill border border-skill/20"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2 mt-4 pt-3 border-t border-border-subtle">
        <button className="text-xs text-foreground-secondary hover:text-foreground transition-colors">
          Edit
        </button>
        <button className="text-xs text-foreground-secondary hover:text-foreground transition-colors">
          Delete
        </button>
        <button className="text-xs text-foreground-secondary hover:text-foreground transition-colors">
          Duplicate
        </button>
      </div>
    </div>
  )
}

function ResourceSidebar({
  tools,
  mcpServers,
  skills,
}: {
  tools: BaseTool[]
  mcpServers: MCPServer[]
  skills: Skill[]
}) {
  const [expandedSections, setExpandedSections] = useState({
    tools: true,
    mcp: true,
    skills: true,
  })

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }))
  }

  return (
    <div className="w-64 border-r border-border bg-background-elevated p-4 overflow-y-auto">
      <h2 className="text-sm font-semibold mb-4">Available Resources</h2>

      <div className="space-y-4">
        <div>
          <button
            onClick={() => toggleSection('tools')}
            className="flex items-center justify-between w-full text-sm font-medium mb-2 hover:text-foreground transition-colors"
          >
            <span>Base Tools ({tools.length})</span>
            <span className="text-xs">{expandedSections.tools ? '▼' : '▸'}</span>
          </button>
          {expandedSections.tools && (
            <div className="space-y-1 pl-2">
              {tools.map((tool) => (
                <div
                  key={tool.name}
                  className="text-xs px-2 py-1.5 rounded hover:bg-background-hover cursor-grab text-tool"
                >
                  {tool.name}
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <button
            onClick={() => toggleSection('mcp')}
            className="flex items-center justify-between w-full text-sm font-medium mb-2 hover:text-foreground transition-colors"
          >
            <span>MCP Servers ({mcpServers.length})</span>
            <span className="text-xs">{expandedSections.mcp ? '▼' : '▸'}</span>
          </button>
          {expandedSections.mcp && (
            <div className="space-y-1 pl-2">
              {mcpServers.map((server) => (
                <div
                  key={server.name}
                  className="text-xs px-2 py-1.5 rounded hover:bg-background-hover cursor-grab text-mcp"
                >
                  {server.name}
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <button
            onClick={() => toggleSection('skills')}
            className="flex items-center justify-between w-full text-sm font-medium mb-2 hover:text-foreground transition-colors"
          >
            <span>Skills ({skills.length})</span>
            <span className="text-xs">{expandedSections.skills ? '▼' : '▸'}</span>
          </button>
          {expandedSections.skills && (
            <div className="space-y-1 pl-2">
              {skills.map((skill) => (
                <div
                  key={skill.name}
                  className="text-xs px-2 py-1.5 rounded hover:bg-background-hover cursor-grab text-skill"
                  title={skill.description}
                >
                  {skill.name}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [projectPath, setProjectPath] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [projectData, setProjectData] = useState<ProjectScanResponse | null>(null)

  const scanProject = async () => {
    if (!projectPath.trim()) {
      setError('Please enter a project path')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/project/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: projectPath }),
      })

      if (!response.ok) {
        throw new Error(`Scan failed: ${response.statusText}`)
      }

      const data: ProjectScanResponse = await response.json()
      setProjectData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to scan project')
    } finally {
      setLoading(false)
    }
  }

  const allMcpServers = projectData
    ? [...projectData.project_mcp_servers, ...projectData.global_mcp_servers]
    : []

  return (
    <div className="h-screen flex flex-col">
      <header className="border-b border-border bg-background-elevated px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Claude Subagent Editor</h1>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Folder className="w-4 h-4 text-foreground-muted" />
              <input
                type="text"
                value={projectPath}
                onChange={(e) => setProjectPath(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && scanProject()}
                placeholder="Enter project path..."
                className="px-3 py-1.5 bg-background border border-border rounded text-sm focus:outline-none focus:ring-2 focus:ring-tool/50 w-80"
              />
            </div>
            <button
              onClick={scanProject}
              disabled={loading}
              className="px-4 py-1.5 bg-tool text-white rounded text-sm font-medium hover:bg-tool/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Scanning...' : 'Scan'}
            </button>
          </div>
        </div>
        {error && (
          <div className="mt-2 text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded px-3 py-2">
            {error}
          </div>
        )}
      </header>

      <div className="flex-1 flex overflow-hidden">
        {projectData && (
          <>
            <ResourceSidebar
              tools={BASE_TOOLS}
              mcpServers={allMcpServers}
              skills={projectData.skills}
            />

            <main className="flex-1 overflow-y-auto p-6">
              <div className="max-w-7xl mx-auto">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-lg font-semibold">Agents</h2>
                    <p className="text-sm text-foreground-secondary">
                      {projectData.agents.length} agent{projectData.agents.length !== 1 ? 's' : ''}{' '}
                      found
                    </p>
                  </div>
                  <button className="flex items-center gap-2 px-4 py-2 bg-tool text-white rounded font-medium hover:bg-tool/90 transition-colors">
                    <Plus className="w-4 h-4" />
                    New Agent
                  </button>
                </div>

                {projectData.agents.length === 0 ? (
                  <div className="text-center py-12 text-foreground-muted">
                    <p>No agents found in {projectData.project_path}/.claude/agents/</p>
                    <p className="text-sm mt-2">Create your first agent to get started</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {projectData.agents.map((agent) => (
                      <AgentCard key={agent.filename} agent={agent} />
                    ))}
                  </div>
                )}
              </div>
            </main>
          </>
        )}

        {!projectData && !loading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Folder className="w-16 h-16 text-foreground-muted mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">Welcome to Claude Subagent Editor</h2>
              <p className="text-foreground-secondary mb-4">
                Enter a project path above to get started
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
