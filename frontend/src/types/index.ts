export type ModelType = 'opus' | 'sonnet' | 'haiku'

export interface AgentConfig {
  filename: string
  name: string
  description: string
  model: ModelType
  tools: string[] | '*'
  disallowedTools: string[]
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

export interface SkillInfo {
  name: string
  path: string
  description: string | null
}

export interface MCPServerInfo {
  name: string
  command: string | null
  url: string | null
  connected: boolean
}

export interface MCPToolInfo {
  name: string
  full_name: string
  description: string | null
}

export interface MCPServerWithTools {
  name: string
  connected: boolean
  error: string | null
  tools: MCPToolInfo[]
}

export interface MCPToolsResponse {
  servers: MCPServerWithTools[]
}

export interface GlobalResourcesResponse {
  skills: SkillInfo[]
  mcp_servers: MCPServerInfo[]
}
