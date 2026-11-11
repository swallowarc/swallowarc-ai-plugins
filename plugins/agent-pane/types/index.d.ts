export type AgentRow = {
  id: string
  type: string
  description: string
  model: string
  status: 'running' | 'done' | 'failed'
  startedAt: number
  endedAt: number | null
  tools: number
  // What the agent is doing now: its latest tool calls, summarized, oldest
  // first. Emptied when it ends.
  recent: string[]
  // The files it wrote (Edit, Write, NotebookEdit), in order of first write.
  files: string[]
  // The head of the agent's final report, once it has ended.
  report: string | null
  // The size of the agent's context at its latest model request, in tokens.
  contextTokens: number
  // The model's context window in tokens, known only when the agent runs on
  // the main loop's model.
  contextWindow: number | null
}

declare module 'claude-code' {
  interface PluginState {
    'agent-pane': {
      agents: Shaped<AgentRow[]>
      now: number
    }
  }
}
