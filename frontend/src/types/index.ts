export type ModelType = 'opus' | 'sonnet' | 'haiku'

export interface AgentConfig {
  filename: string
  name: string
  description: string
  model: ModelType
  tools: string[]
  skills: string[]
  nickname: string | null
  body: string
}

export interface ProjectScanResponse {
  path: string
  agents: AgentConfig[]
  mcp_servers: string[]
  agent_count: number
}

export interface HealthResponse {
  status: string
  version: string
}

export interface Project {
  path: string
  name: string
  lastOpened?: string
}
