export type AgentRow = {
  id: string
  type: string
  description: string
  model: string
  status: 'running' | 'done' | 'failed'
  startedAt: number
  endedAt: number | null
  tools: number
  // What the agent is doing now: its latest tool call, summarized.
  activity: string | null
  // The head of the agent's final report, once it has ended.
  report: string | null
  // The size of the agent's context at its latest model request, in tokens.
  contextTokens: number
}

declare module 'claude-code' {
  interface PluginState {
    'agent-pane': {
      agents: Shaped<AgentRow[]>
      now: number
    }
  }
}
