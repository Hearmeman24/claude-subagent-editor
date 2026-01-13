export type ModelType = 'opus' | 'sonnet' | 'haiku'

export interface AgentConfig {
  name: string
  description: string
  model: ModelType
  tools?: string[]
  skills?: string[]
  nickname?: string
  filename: string
  markdown_body: string
}

export interface MCPServer {
  name: string
  command: string
  args: string[]
  env?: Record<string, string>
}

export interface Skill {
  name: string
  description: string
}

export interface BaseTool {
  name: string
  category: 'file' | 'execution' | 'code' | 'web' | 'notebook' | 'utility'
}

export interface ProjectScanResponse {
  agents: AgentConfig[]
  project_mcp_servers: MCPServer[]
  global_mcp_servers: MCPServer[]
  skills: Skill[]
  project_path: string
}

export interface HealthResponse {
  status: string
  version: string
}
