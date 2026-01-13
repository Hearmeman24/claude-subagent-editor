import { useState, useEffect } from 'react'
import { Folder, Plus, X, ChevronRight } from 'lucide-react'
import type { Project } from '@/types'

const STORAGE_KEY = 'claude-subagent-editor-projects'

interface ProjectPickerProps {
  onSelectProject: (path: string) => void
}

export default function ProjectPicker({ onSelectProject }: ProjectPickerProps) {
  const [projects, setProjects] = useState<Project[]>([])
  const [newProjectPath, setNewProjectPath] = useState('')
  const [showAddForm, setShowAddForm] = useState(false)

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        setProjects(JSON.parse(stored))
      }
    } catch (error) {
      console.error('Failed to load projects:', error)
    }
  }

  const saveProjects = (updatedProjects: Project[]) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedProjects))
      setProjects(updatedProjects)
    } catch (error) {
      console.error('Failed to save projects:', error)
    }
  }

  const addProject = () => {
    if (!newProjectPath.trim()) return

    const pathSegments = newProjectPath.trim().split('/')
    const name = pathSegments[pathSegments.length - 1] || 'Unknown'

    const newProject: Project = {
      path: newProjectPath.trim(),
      name,
      lastOpened: new Date().toISOString(),
    }

    const updatedProjects = [...projects, newProject]
    saveProjects(updatedProjects)
    setNewProjectPath('')
    setShowAddForm(false)
  }

  const removeProject = (path: string) => {
    const updatedProjects = projects.filter((p) => p.path !== path)
    saveProjects(updatedProjects)
  }

  const selectProject = (project: Project) => {
    const updatedProjects = projects.map((p) =>
      p.path === project.path ? { ...p, lastOpened: new Date().toISOString() } : p
    )
    saveProjects(updatedProjects)
    onSelectProject(project.path)
  }

  const sortedProjects = [...projects].sort((a, b) => {
    const aTime = a.lastOpened ? new Date(a.lastOpened).getTime() : 0
    const bTime = b.lastOpened ? new Date(b.lastOpened).getTime() : 0
    return bTime - aTime
  })

  return (
    <div className="h-screen flex flex-col bg-background">
      <header className="border-b border-border bg-background-elevated px-6 py-4">
        <h1 className="text-xl font-semibold">Claude Subagent Editor</h1>
        <p className="text-sm text-foreground-secondary mt-1">Select a project to get started</p>
      </header>

      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold">Your Projects</h2>
            <button
              onClick={() => setShowAddForm(true)}
              className="flex items-center gap-2 px-4 py-2 bg-tool text-white rounded font-medium hover:bg-tool/90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Project
            </button>
          </div>

          {showAddForm && (
            <div className="mb-6 p-4 border border-border rounded-lg bg-background-elevated">
              <h3 className="text-sm font-medium mb-3">Add New Project</h3>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newProjectPath}
                  onChange={(e) => setNewProjectPath(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addProject()}
                  placeholder="/path/to/project"
                  className="flex-1 px-3 py-2 bg-background border border-border rounded text-sm focus:outline-none focus:ring-2 focus:ring-tool/50"
                  autoFocus
                />
                <button
                  onClick={addProject}
                  disabled={!newProjectPath.trim()}
                  className="px-4 py-2 bg-tool text-white rounded text-sm font-medium hover:bg-tool/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Add
                </button>
                <button
                  onClick={() => {
                    setShowAddForm(false)
                    setNewProjectPath('')
                  }}
                  className="px-4 py-2 bg-background border border-border rounded text-sm font-medium hover:bg-background-hover transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {sortedProjects.length === 0 ? (
            <div className="text-center py-16">
              <Folder className="w-16 h-16 text-foreground-muted mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No projects yet</h3>
              <p className="text-foreground-secondary mb-4">
                Add your first project to get started
              </p>
              {!showAddForm && (
                <button
                  onClick={() => setShowAddForm(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-tool text-white rounded font-medium hover:bg-tool/90 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  Add Project
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              {sortedProjects.map((project) => (
                <div
                  key={project.path}
                  className="group flex items-center justify-between p-4 border border-border rounded-lg bg-background-elevated hover:bg-background-hover transition-colors cursor-pointer"
                  onClick={() => selectProject(project)}
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <Folder className="w-5 h-5 text-tool flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-base">{project.name}</h3>
                      <p className="text-sm text-foreground-secondary truncate">
                        {project.path}
                      </p>
                      {project.lastOpened && (
                        <p className="text-xs text-foreground-muted mt-1">
                          Last opened: {new Date(project.lastOpened).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        removeProject(project.path)
                      }}
                      className="p-2 text-foreground-muted hover:text-foreground hover:bg-background rounded opacity-0 group-hover:opacity-100 transition-all"
                      title="Remove project"
                    >
                      <X className="w-4 h-4" />
                    </button>
                    <ChevronRight className="w-5 h-5 text-foreground-muted" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
