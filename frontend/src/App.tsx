import { useState } from 'react'
import { Folder, Plus, X } from 'lucide-react'
import type { AgentConfig, ProjectScanResponse, ModelType } from '@/types'
import { cn } from '@/lib/utils'

interface BaseTool {
  name: string
  category: 'file' | 'execution' | 'code' | 'web' | 'notebook' | 'utility'
}

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

const modelColors = {
  opus: 'text-opus',
  sonnet: 'text-sonnet',
  haiku: 'text-haiku',
}

interface AgentEditorProps {
  agent: AgentConfig
  onClose: () => void
  onSave: (updatedAgent: AgentConfig) => void
}

function AgentEditor({ agent, onClose, onSave }: AgentEditorProps) {
  const [editedAgent, setEditedAgent] = useState<AgentConfig>({ ...agent })
  const [toolInput, setToolInput] = useState('')
  const [skillInput, setSkillInput] = useState('')

  const handleSave = async () => {
    try {
      const response = await fetch(`/api/agents/${agent.filename}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editedAgent),
      })

      if (!response.ok) {
        throw new Error(`Failed to save: ${response.statusText}`)
      }

      onSave(editedAgent)
      onClose()
    } catch (err) {
      console.error('Failed to save agent:', err)
      alert('Failed to save agent. The backend endpoint may not be implemented yet.')
    }
  }

  const addTool = () => {
    if (toolInput.trim() && !editedAgent.tools.includes(toolInput.trim())) {
      setEditedAgent({
        ...editedAgent,
        tools: [...editedAgent.tools, toolInput.trim()],
      })
      setToolInput('')
    }
  }

  const removeTool = (tool: string) => {
    setEditedAgent({
      ...editedAgent,
      tools: editedAgent.tools.filter((t) => t !== tool),
    })
  }

  const addSkill = () => {
    if (skillInput.trim() && !editedAgent.skills.includes(skillInput.trim())) {
      setEditedAgent({
        ...editedAgent,
        skills: [...editedAgent.skills, skillInput.trim()],
      })
      setSkillInput('')
    }
  }

  const removeSkill = (skill: string) => {
    setEditedAgent({
      ...editedAgent,
      skills: editedAgent.skills.filter((s) => s !== skill),
    })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background border border-border rounded-lg w-full max-w-3xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold">Edit Agent</h2>
          <button
            onClick={onClose}
            className="text-foreground-secondary hover:text-foreground transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">Name</label>
            <input
              type="text"
              value={editedAgent.name}
              onChange={(e) => setEditedAgent({ ...editedAgent, name: e.target.value })}
              className="w-full px-3 py-2 bg-background-elevated border border-border rounded text-sm focus:outline-none focus:ring-2 focus:ring-tool/50"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Nickname (optional)</label>
            <input
              type="text"
              value={editedAgent.nickname || ''}
              onChange={(e) => setEditedAgent({ ...editedAgent, nickname: e.target.value || null })}
              className="w-full px-3 py-2 bg-background-elevated border border-border rounded text-sm focus:outline-none focus:ring-2 focus:ring-tool/50"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Description</label>
            <textarea
              value={editedAgent.description}
              onChange={(e) => setEditedAgent({ ...editedAgent, description: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 bg-background-elevated border border-border rounded text-sm focus:outline-none focus:ring-2 focus:ring-tool/50 resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Model</label>
            <select
              value={editedAgent.model}
              onChange={(e) => setEditedAgent({ ...editedAgent, model: e.target.value as ModelType })}
              className="w-full px-3 py-2 bg-background-elevated border border-border rounded text-sm focus:outline-none focus:ring-2 focus:ring-tool/50"
            >
              <option value="opus">Opus</option>
              <option value="sonnet">Sonnet</option>
              <option value="haiku">Haiku</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Tools</label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={toolInput}
                onChange={(e) => setToolInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addTool()}
                placeholder="Add tool..."
                className="flex-1 px-3 py-2 bg-background-elevated border border-border rounded text-sm focus:outline-none focus:ring-2 focus:ring-tool/50"
              />
              <button
                onClick={addTool}
                className="px-4 py-2 bg-tool text-white rounded text-sm font-medium hover:bg-tool/90 transition-colors"
              >
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {editedAgent.tools.map((tool) => (
                <span
                  key={tool}
                  className="px-2 py-1 text-xs rounded bg-tool-bg text-tool border border-tool/20 flex items-center gap-1.5"
                >
                  {tool}
                  <button
                    onClick={() => removeTool(tool)}
                    className="hover:text-foreground transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Skills</label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addSkill()}
                placeholder="Add skill..."
                className="flex-1 px-3 py-2 bg-background-elevated border border-border rounded text-sm focus:outline-none focus:ring-2 focus:ring-tool/50"
              />
              <button
                onClick={addSkill}
                className="px-4 py-2 bg-tool text-white rounded text-sm font-medium hover:bg-tool/90 transition-colors"
              >
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {editedAgent.skills.map((skill) => (
                <span
                  key={skill}
                  className="px-2 py-1 text-xs rounded bg-skill-bg text-skill border border-skill/20 flex items-center gap-1.5"
                >
                  {skill}
                  <button
                    onClick={() => removeSkill(skill)}
                    className="hover:text-foreground transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Body (Markdown)</label>
            <textarea
              value={editedAgent.body}
              onChange={(e) => setEditedAgent({ ...editedAgent, body: e.target.value })}
              rows={10}
              className="w-full px-3 py-2 bg-background-elevated border border-border rounded text-sm font-mono focus:outline-none focus:ring-2 focus:ring-tool/50 resize-none"
              placeholder="Agent instructions in markdown..."
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-4 border-t border-border">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-foreground-secondary hover:text-foreground transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-tool text-white rounded text-sm font-medium hover:bg-tool/90 transition-colors"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  )
}

function AgentCard({ agent, onEdit }: { agent: AgentConfig; onEdit: (agent: AgentConfig) => void }) {

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

      {agent.tools.length > 0 && (
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

      {agent.skills.length > 0 && (
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
        <button
          onClick={() => onEdit(agent)}
          className="text-xs text-foreground-secondary hover:text-foreground transition-colors"
        >
          Edit
        </button>
        <button
          onClick={() => console.log('Delete agent:', agent.name)}
          className="text-xs text-foreground-secondary hover:text-foreground transition-colors"
        >
          Delete
        </button>
        <button
          onClick={() => console.log('Duplicate agent:', agent.name)}
          className="text-xs text-foreground-secondary hover:text-foreground transition-colors"
        >
          Duplicate
        </button>
      </div>
    </div>
  )
}

function ResourceSidebar({
  tools,
  mcpServers,
}: {
  tools: BaseTool[]
  mcpServers: string[]
}) {
  const [expandedSections, setExpandedSections] = useState({
    tools: true,
    mcp: true,
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
                  key={server}
                  className="text-xs px-2 py-1.5 rounded hover:bg-background-hover cursor-grab text-mcp"
                >
                  {server}
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
  const [editingAgent, setEditingAgent] = useState<AgentConfig | null>(null)

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

  const handleEditAgent = (agent: AgentConfig) => {
    setEditingAgent(agent)
  }

  const handleSaveAgent = (updatedAgent: AgentConfig) => {
    if (!projectData) return

    setProjectData({
      ...projectData,
      agents: projectData.agents.map((a) =>
        a.filename === updatedAgent.filename ? updatedAgent : a
      ),
    })
  }

  const allMcpServers = projectData ? projectData.mcp_servers : []

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
                  <button
                    onClick={() => console.log('Create new agent')}
                    className="flex items-center gap-2 px-4 py-2 bg-tool text-white rounded font-medium hover:bg-tool/90 transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    New Agent
                  </button>
                </div>

                {projectData.agents.length === 0 ? (
                  <div className="text-center py-12 text-foreground-muted">
                    <p>No agents found in {projectData.path}/.claude/agents/</p>
                    <p className="text-sm mt-2">Create your first agent to get started</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {projectData.agents.map((agent) => (
                      <AgentCard key={agent.filename} agent={agent} onEdit={handleEditAgent} />
                    ))}
                  </div>
                )}
              </div>
            </main>
          </>
        )}

        {loading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tool mx-auto mb-4"></div>
              <p className="text-foreground-secondary">Scanning project...</p>
            </div>
          </div>
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

      {editingAgent && (
        <AgentEditor
          agent={editingAgent}
          onClose={() => setEditingAgent(null)}
          onSave={handleSaveAgent}
        />
      )}
    </div>
  )
}
