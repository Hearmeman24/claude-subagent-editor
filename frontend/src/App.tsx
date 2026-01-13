import { useState, useEffect } from 'react'
import { ArrowLeft, X, ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react'
import type { AgentConfig, ProjectScanResponse, ModelType, SkillInfo, MCPServerInfo, GlobalResourcesResponse, MCPServerWithTools } from '@/types'
import { cn } from '@/lib/utils'
import ProjectPicker from '@/components/ProjectPicker'

const modelColors = {
  opus: 'text-opus',
  sonnet: 'text-sonnet',
  haiku: 'text-haiku',
}

const DEFAULT_CLAUDE_TOOLS = [
  'Read', 'Write', 'Edit', 'Bash', 'Glob', 'Grep',
  'Task', 'WebFetch', 'WebSearch', 'NotebookEdit',
  'TodoWrite', 'AskUserQuestion', 'Skill', 'LSP'
]

interface AgentEditorProps {
  agent: AgentConfig
  onClose: () => void
  onSave: (updatedAgent: AgentConfig) => void
  globalResources: GlobalResourcesResponse
}

interface DragDropZoneProps {
  items: string[]
  type: 'skill' | 'tool' | 'mcp'
  colorClass: string
  bgClass: string
  onAdd: (item: string) => void
  onRemove: (item: string) => void
  dropActive: boolean
  onDragOver: (e: React.DragEvent) => void
  onDragLeave: () => void
  onDrop: (e: React.DragEvent) => void
  label: string
  dragStartHandler: (e: React.DragEvent, item: string) => void
}

function DragDropZone({
  items,
  type,
  colorClass,
  bgClass,
  onRemove,
  dropActive,
  onDragOver,
  onDragLeave,
  onDrop,
  label,
  dragStartHandler,
}: DragDropZoneProps) {
  return (
    <div className="flex-1">
      <div className="text-xs font-medium text-foreground-secondary mb-2">{label}</div>
      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        className={cn(
          'min-h-[200px] max-h-[200px] overflow-y-auto p-3 rounded border-2 border-dashed transition-colors',
          dropActive ? `border-${type} bg-${type}/10` : 'border-border bg-background-elevated',
          'flex flex-wrap gap-2 content-start'
        )}
      >
        {items.length === 0 && (
          <span className="text-xs text-foreground-muted italic">
            {label === 'Available' ? 'No more items available' : 'Drag items here'}
          </span>
        )}
        {items.map((item) => (
          <span
            key={item}
            draggable
            onDragStart={(e) => dragStartHandler(e, item)}
            className={cn(
              'px-2 py-1 text-xs rounded border flex items-center gap-1.5 h-fit cursor-grab active:cursor-grabbing',
              bgClass,
              colorClass,
              `border-${type}/20`
            )}
          >
            {item}
            {label === 'Assigned' && (
              <button
                onClick={() => onRemove(item)}
                className="hover:text-foreground transition-colors"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </span>
        ))}
      </div>
    </div>
  )
}

function AgentEditor({ agent, onClose, onSave, globalResources }: AgentEditorProps) {
  const [editedAgent, setEditedAgent] = useState<AgentConfig>({ ...agent })
  const [activeTab, setActiveTab] = useState<'tools' | 'skills' | 'mcp'>('tools')
  const [availableDropActive, setAvailableDropActive] = useState(false)
  const [assignedDropActive, setAssignedDropActive] = useState(false)
  const [mcpServers, setMcpServers] = useState<MCPServerWithTools[]>([])
  const [expandedServers, setExpandedServers] = useState<Record<string, boolean>>({})

  // Fetch MCP tools on mount
  useEffect(() => {
    const fetchMcpTools = async () => {
      try {
        const response = await fetch('/api/mcp/tools')
        if (response.ok) {
          const data = await response.json()
          setMcpServers(data.servers)
          // Auto-expand all servers by default
          const expanded: Record<string, boolean> = {}
          data.servers.forEach((server: MCPServerWithTools) => {
            expanded[server.name] = true
          })
          setExpandedServers(expanded)
        }
      } catch (err) {
        console.error('Failed to fetch MCP tools:', err)
      }
    }
    fetchMcpTools()
  }, [])

  // Separate base tools from MCP tools in agent's tools array
  const agentBaseTools = editedAgent.tools.filter(t => !t.startsWith('mcp__'))
  const agentMcpTools = editedAgent.tools.filter(t => t.startsWith('mcp__'))

  // Filter available items to exclude already assigned ones
  const availableSkills = globalResources.skills
    .map((s) => s.name)
    .filter((name) => !editedAgent.skills.includes(name))

  const availableBaseTools = DEFAULT_CLAUDE_TOOLS
    .filter((name) => !agentBaseTools.includes(name))

  const handleSave = async () => {
    try {
      // Only send fields the backend expects (exclude filename, nickname)
      const payload = {
        name: editedAgent.name,
        description: editedAgent.description,
        model: editedAgent.model,
        tools: editedAgent.tools,
        skills: editedAgent.skills,
        body: editedAgent.body,
      };

      const response = await fetch(`/api/agent/${agent.filename}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
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

  const addBaseTool = (tool: string) => {
    if (!editedAgent.tools.includes(tool)) {
      setEditedAgent({
        ...editedAgent,
        tools: [...editedAgent.tools, tool],
      })
    }
  }

  const removeBaseTool = (tool: string) => {
    setEditedAgent({
      ...editedAgent,
      tools: editedAgent.tools.filter((t) => t !== tool),
    })
  }

  const addMcpTool = (fullName: string) => {
    if (!editedAgent.tools.includes(fullName)) {
      setEditedAgent({
        ...editedAgent,
        tools: [...editedAgent.tools, fullName],
      })
    }
  }

  const removeMcpTool = (fullName: string) => {
    setEditedAgent({
      ...editedAgent,
      tools: editedAgent.tools.filter((t) => t !== fullName),
    })
  }

  const toggleServer = (serverName: string) => {
    setExpandedServers(prev => ({
      ...prev,
      [serverName]: !prev[serverName]
    }))
  }

  const addSkill = (skill: string) => {
    if (!editedAgent.skills.includes(skill)) {
      setEditedAgent({
        ...editedAgent,
        skills: [...editedAgent.skills, skill],
      })
    }
  }

  const removeSkill = (skill: string) => {
    setEditedAgent({
      ...editedAgent,
      skills: editedAgent.skills.filter((s) => s !== skill),
    })
  }

  const handleDragStart = (e: React.DragEvent, type: 'skill' | 'tool' | 'mcp', name: string, source: 'available' | 'assigned') => {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', JSON.stringify({ type, name, source }))
  }

  const handleAvailableDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setAvailableDropActive(false)

    try {
      const data = JSON.parse(e.dataTransfer.getData('text/plain'))
      if (data.source === 'assigned') {
        if (activeTab === 'skills' && data.type === 'skill') {
          removeSkill(data.name)
        } else if (activeTab === 'tools' && data.type === 'tool') {
          removeBaseTool(data.name)
        } else if (activeTab === 'mcp' && data.type === 'mcp') {
          removeMcpTool(data.name)
        }
      }
    } catch (err) {
      console.error('Invalid drag data:', err)
    }
  }

  const handleAssignedDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setAssignedDropActive(false)

    try {
      const data = JSON.parse(e.dataTransfer.getData('text/plain'))
      if (data.source === 'available') {
        if (activeTab === 'skills' && data.type === 'skill') {
          addSkill(data.name)
        } else if (activeTab === 'tools' && data.type === 'tool') {
          addBaseTool(data.name)
        } else if (activeTab === 'mcp' && data.type === 'mcp') {
          addMcpTool(data.name)
        }
      }
    } catch (err) {
      console.error('Invalid drag data:', err)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background border border-border rounded-lg w-full max-w-4xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold">Edit: {editedAgent.name || 'Untitled'}</h2>
          <button
            onClick={onClose}
            className="text-foreground-secondary hover:text-foreground transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* Top section: Name, Description, Model */}
          <div className="grid grid-cols-2 gap-4">
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
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Description</label>
            <textarea
              value={editedAgent.description}
              onChange={(e) => setEditedAgent({ ...editedAgent, description: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 bg-background-elevated border border-border rounded text-sm focus:outline-none focus:ring-2 focus:ring-tool/50 resize-none"
            />
          </div>

          {/* Tab selector */}
          <div className="border-t border-border pt-4">
            <div className="flex gap-4 mb-4">
              <button
                onClick={() => setActiveTab('tools')}
                className={cn(
                  'px-4 py-2 text-sm font-medium transition-colors border-b-2',
                  activeTab === 'tools'
                    ? 'border-tool text-tool'
                    : 'border-transparent text-foreground-secondary hover:text-foreground'
                )}
              >
                Tools
              </button>
              <button
                onClick={() => setActiveTab('skills')}
                className={cn(
                  'px-4 py-2 text-sm font-medium transition-colors border-b-2',
                  activeTab === 'skills'
                    ? 'border-skill text-skill'
                    : 'border-transparent text-foreground-secondary hover:text-foreground'
                )}
              >
                Skills
              </button>
              <button
                onClick={() => setActiveTab('mcp')}
                className={cn(
                  'px-4 py-2 text-sm font-medium transition-colors border-b-2',
                  activeTab === 'mcp'
                    ? 'border-mcp text-mcp'
                    : 'border-transparent text-foreground-secondary hover:text-foreground'
                )}
              >
                MCP
              </button>
            </div>

            {/* Two-column drag-drop */}
            <div className="flex gap-4">
              {activeTab === 'tools' && (
                <>
                  <DragDropZone
                    items={availableBaseTools}
                    type="tool"
                    colorClass="text-tool"
                    bgClass="bg-tool-bg"
                    onAdd={addBaseTool}
                    onRemove={removeBaseTool}
                    dropActive={availableDropActive}
                    onDragOver={(e) => {
                      handleDragOver(e)
                      setAvailableDropActive(true)
                    }}
                    onDragLeave={() => setAvailableDropActive(false)}
                    onDrop={handleAvailableDrop}
                    label="Available"
                    dragStartHandler={(e, item) => handleDragStart(e, 'tool', item, 'available')}
                  />
                  <DragDropZone
                    items={agentBaseTools}
                    type="tool"
                    colorClass="text-tool"
                    bgClass="bg-tool-bg"
                    onAdd={addBaseTool}
                    onRemove={removeBaseTool}
                    dropActive={assignedDropActive}
                    onDragOver={(e) => {
                      handleDragOver(e)
                      setAssignedDropActive(true)
                    }}
                    onDragLeave={() => setAssignedDropActive(false)}
                    onDrop={handleAssignedDrop}
                    label="Assigned"
                    dragStartHandler={(e, item) => handleDragStart(e, 'tool', item, 'assigned')}
                  />
                </>
              )}

              {activeTab === 'skills' && (
                <>
                  <DragDropZone
                    items={availableSkills}
                    type="skill"
                    colorClass="text-skill"
                    bgClass="bg-skill-bg"
                    onAdd={addSkill}
                    onRemove={removeSkill}
                    dropActive={availableDropActive}
                    onDragOver={(e) => {
                      handleDragOver(e)
                      setAvailableDropActive(true)
                    }}
                    onDragLeave={() => setAvailableDropActive(false)}
                    onDrop={handleAvailableDrop}
                    label="Available"
                    dragStartHandler={(e, item) => handleDragStart(e, 'skill', item, 'available')}
                  />
                  <div className="flex-1">
                    <DragDropZone
                      items={editedAgent.skills}
                      type="skill"
                      colorClass="text-skill"
                      bgClass="bg-skill-bg"
                      onAdd={addSkill}
                      onRemove={removeSkill}
                      dropActive={assignedDropActive}
                      onDragOver={(e) => {
                        handleDragOver(e)
                        setAssignedDropActive(true)
                      }}
                      onDragLeave={() => setAssignedDropActive(false)}
                      onDrop={handleAssignedDrop}
                      label="Assigned"
                      dragStartHandler={(e, item) => handleDragStart(e, 'skill', item, 'assigned')}
                    />
                    {editedAgent.skills.length > 0 && !editedAgent.tools.includes('Skill') && (
                      <div className="text-amber-500 text-sm mt-2 flex items-center gap-1.5">
                        <span>⚠</span>
                        <span>The "Skill" base tool is required to invoke skills</span>
                      </div>
                    )}
                  </div>
                </>
              )}

              {activeTab === 'mcp' && (
                <>
                  {/* Available MCP Tools - Grouped by Server */}
                  <div className="flex-1">
                    <div className="text-xs font-medium text-foreground-secondary mb-2">Available</div>
                    <div
                      onDrop={handleAvailableDrop}
                      onDragOver={(e) => {
                        handleDragOver(e)
                        setAvailableDropActive(true)
                      }}
                      onDragLeave={() => setAvailableDropActive(false)}
                      className={cn(
                        'min-h-[200px] max-h-[200px] overflow-y-auto p-3 rounded border-2 border-dashed transition-colors',
                        availableDropActive ? 'border-mcp bg-mcp/10' : 'border-border bg-background-elevated'
                      )}
                    >
                      {mcpServers.length === 0 && (
                        <span className="text-xs text-foreground-muted italic">Loading MCP tools...</span>
                      )}
                      {mcpServers.map((server) => {
                        const availableTools = server.tools.filter(
                          tool => !agentMcpTools.includes(tool.full_name)
                        )
                        if (availableTools.length === 0 && server.connected) return null

                        return (
                          <div key={server.name} className="mb-3 last:mb-0">
                            <button
                              onClick={() => toggleServer(server.name)}
                              className="flex items-center gap-1.5 w-full text-xs font-medium text-foreground-secondary hover:text-foreground transition-colors mb-1.5"
                            >
                              {expandedServers[server.name] ? (
                                <ChevronDown className="w-3 h-3" />
                              ) : (
                                <ChevronRight className="w-3 h-3" />
                              )}
                              <span>{server.name}</span>
                              {server.connected ? (
                                <span className="text-green-500">✓</span>
                              ) : (
                                <span className="text-amber-500" title={server.error || 'Not connected'}>
                                  <AlertTriangle className="w-3 h-3" />
                                </span>
                              )}
                            </button>
                            {expandedServers[server.name] && (
                              <div className="pl-4 space-y-1">
                                {!server.connected && (
                                  <div className="text-xs text-foreground-muted italic">
                                    {server.error || 'No tools available'}
                                  </div>
                                )}
                                {availableTools.map((tool) => (
                                  <span
                                    key={tool.full_name}
                                    draggable
                                    onDragStart={(e) => handleDragStart(e, 'mcp', tool.full_name, 'available')}
                                    className="px-2 py-1 text-xs rounded border flex items-center gap-1.5 cursor-grab active:cursor-grabbing bg-mcp-bg text-mcp border-mcp/20"
                                    title={tool.description || tool.name}
                                  >
                                    {tool.name}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Assigned MCP Tools */}
                  <div className="flex-1">
                    <div className="text-xs font-medium text-foreground-secondary mb-2">Assigned</div>
                    <div
                      onDrop={handleAssignedDrop}
                      onDragOver={(e) => {
                        handleDragOver(e)
                        setAssignedDropActive(true)
                      }}
                      onDragLeave={() => setAssignedDropActive(false)}
                      className={cn(
                        'min-h-[200px] max-h-[200px] overflow-y-auto p-3 rounded border-2 border-dashed transition-colors',
                        assignedDropActive ? 'border-mcp bg-mcp/10' : 'border-border bg-background-elevated',
                        'flex flex-wrap gap-2 content-start'
                      )}
                    >
                      {agentMcpTools.length === 0 && (
                        <span className="text-xs text-foreground-muted italic">Drag tools here</span>
                      )}
                      {agentMcpTools.map((fullName) => {
                        // Extract display name from full_name
                        const parts = fullName.split('__')
                        const displayName = parts.length >= 3 ? parts[2] : fullName

                        return (
                          <span
                            key={fullName}
                            draggable
                            onDragStart={(e) => handleDragStart(e, 'mcp', fullName, 'assigned')}
                            className="px-2 py-1 text-xs rounded border flex items-center gap-1.5 h-fit cursor-grab active:cursor-grabbing bg-mcp-bg text-mcp border-mcp/20"
                            title={fullName}
                          >
                            {displayName}
                            <button
                              onClick={() => removeMcpTool(fullName)}
                              className="hover:text-foreground transition-colors"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </span>
                        )
                      })}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Body section */}
          <div className="border-t border-border pt-4">
            <label className="block text-sm font-medium mb-1.5">Body (Markdown)</label>
            <textarea
              value={editedAgent.body}
              onChange={(e) => setEditedAgent({ ...editedAgent, body: e.target.value })}
              rows={8}
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
            Save
          </button>
        </div>
      </div>
    </div>
  )
}

function AgentCard({ agent, onEdit }: { agent: AgentConfig; onEdit: (agent: AgentConfig) => void }) {

  return (
    <div className="border border-border rounded-lg p-4 bg-background-elevated hover:bg-background-hover transition-colors flex flex-col h-full">
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

      <div className="flex gap-2 mt-auto pt-3 border-t border-border-subtle">
        <button
          onClick={() => onEdit(agent)}
          className="text-xs text-foreground-secondary hover:text-foreground transition-colors"
        >
          Edit
        </button>
      </div>
    </div>
  )
}

function ResourceSidebar({
  skills,
  mcpServers,
}: {
  skills: SkillInfo[]
  mcpServers: MCPServerInfo[]
}) {
  const [expandedSections, setExpandedSections] = useState({
    baseTools: true,
    skills: true,
    mcp: true,
  })

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }))
  }

  const handleDragStart = (e: React.DragEvent, type: 'skill' | 'mcp', name: string) => {
    e.dataTransfer.effectAllowed = 'copy'
    e.dataTransfer.setData('text/plain', JSON.stringify({ type, name }))
  }

  return (
    <div className="w-64 border-r border-border bg-background-elevated p-4 overflow-y-auto">
      <h2 className="text-sm font-semibold mb-4">Available Resources</h2>

      <div className="space-y-4">
        <div>
          <button
            onClick={() => toggleSection('baseTools')}
            className="flex items-center justify-between w-full text-sm font-medium mb-2 hover:text-foreground transition-colors"
          >
            <span>Base Tools ({DEFAULT_CLAUDE_TOOLS.length})</span>
            <span className="text-xs">{expandedSections.baseTools ? '▼' : '▸'}</span>
          </button>
          {expandedSections.baseTools && (
            <div className="space-y-1 pl-2">
              {DEFAULT_CLAUDE_TOOLS.map((tool) => (
                <div
                  key={tool}
                  className="text-xs px-2 py-1.5 rounded text-tool"
                  title={tool}
                >
                  {tool}
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
                  draggable
                  onDragStart={(e) => handleDragStart(e, 'skill', skill.name)}
                  className="text-xs px-2 py-1.5 rounded hover:bg-background-hover cursor-grab active:cursor-grabbing text-skill"
                  title={skill.description || skill.path}
                >
                  {skill.name}
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
                  draggable
                  onDragStart={(e) => handleDragStart(e, 'mcp', server.name)}
                  className="text-xs px-2 py-1.5 rounded hover:bg-background-hover cursor-grab active:cursor-grabbing text-mcp flex items-center gap-2"
                  title={server.command || server.url || ''}
                >
                  <span
                    className={cn(
                      'w-2 h-2 rounded-full',
                      server.connected ? 'bg-green-500' : 'bg-gray-500'
                    )}
                  />
                  {server.name}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

type ViewState = 'projects' | 'agents'

export default function App() {
  const [viewState, setViewState] = useState<ViewState>('projects')
  const [currentProjectPath, setCurrentProjectPath] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [projectData, setProjectData] = useState<ProjectScanResponse | null>(null)
  const [editingAgent, setEditingAgent] = useState<AgentConfig | null>(null)
  const [globalResources, setGlobalResources] = useState<GlobalResourcesResponse>({
    skills: [],
    mcp_servers: [],
  })

  useEffect(() => {
    const fetchGlobalResources = async () => {
      try {
        const response = await fetch('/api/resources/global')
        if (response.ok) {
          const data: GlobalResourcesResponse = await response.json()
          setGlobalResources(data)
        }
      } catch (err) {
        console.error('Failed to fetch global resources:', err)
      }
    }

    fetchGlobalResources()
  }, [])

  const handleSelectProject = async (path: string) => {
    setCurrentProjectPath(path)
    setLoading(true)
    setError(null)
    setViewState('agents')

    try {
      const response = await fetch('/api/project/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      })

      if (!response.ok) {
        throw new Error(`Scan failed: ${response.statusText}`)
      }

      const data: ProjectScanResponse = await response.json()
      setProjectData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to scan project')
      setViewState('projects')
    } finally {
      setLoading(false)
    }
  }

  const handleBackToProjects = () => {
    setViewState('projects')
    setProjectData(null)
    setCurrentProjectPath('')
    setError(null)
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

  if (viewState === 'projects') {
    return <ProjectPicker onSelectProject={handleSelectProject} />
  }

  return (
    <div className="h-screen flex flex-col pb-12">
      <header className="border-b border-border bg-background-elevated px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={handleBackToProjects}
              className="p-2 hover:bg-background-hover rounded transition-colors"
              title="Back to projects"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-semibold">Claude Subagent Editor</h1>
              {currentProjectPath && (
                <p className="text-sm text-foreground-secondary">{currentProjectPath}</p>
              )}
            </div>
          </div>
        </div>
        {error && (
          <div className="mt-2 text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded px-3 py-2">
            {error}
          </div>
        )}
      </header>

      <div className="flex-1 flex overflow-hidden">
        {projectData && !loading && (
          <>
            <ResourceSidebar
              skills={globalResources.skills}
              mcpServers={globalResources.mcp_servers}
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
                </div>

                {projectData.agents.length === 0 ? (
                  <div className="text-center py-12 text-foreground-muted">
                    <p>No agents found in {projectData.path}/.claude/agents/</p>
                    <p className="text-sm mt-2">Create your first agent to get started</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 items-stretch">
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
      </div>

      {editingAgent && (
        <AgentEditor
          agent={editingAgent}
          onClose={() => setEditingAgent(null)}
          onSave={handleSaveAgent}
          globalResources={globalResources}
        />
      )}

      <footer className="fixed bottom-0 left-0 right-0 bg-zinc-900 border-t border-zinc-800 py-2 px-4 text-center text-sm text-zinc-400">
        <div className="flex items-center justify-center gap-2">
          <span>Created by</span>
          <a
            href="https://github.com/Hearmeman24"
            target="_blank"
            rel="noopener noreferrer"
            className="text-zinc-200 hover:text-white flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
            Hearmeman24
          </a>
          <span className="mx-2">•</span>
          <a
            href="https://github.com/Hearmeman24/claude-subagent-editor"
            target="_blank"
            rel="noopener noreferrer"
            className="text-zinc-200 hover:text-white"
          >
            Star & contribute on GitHub
          </a>
        </div>
      </footer>
    </div>
  )
}
