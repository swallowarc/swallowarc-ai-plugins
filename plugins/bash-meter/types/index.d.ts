export type Run = {
  ms: number
  // The exit code where the result names one; null on success or when unknown.
  exitCode: number | null
  hasFailed: boolean
  isBackground: boolean
}

declare module 'claude-code' {
  interface PluginState {
    'bash-meter': { runs: StateFamily<Run | null> }
  }
}
