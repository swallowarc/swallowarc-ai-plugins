import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { AgentRow } from '../types'

const PANE = 'agents'
const TITLE = 'Agents'
const KEPT = 50
const ACTIVITY_CHARS = 160
const REPORT_CHARS = 400
const REPORT_ROWS = 2

// Change the tag when a row's fields change: it declines what an earlier
// version stored, which outlives a reload.
const agents = atom({ plugin: 'agent-pane', key: 'agents' } as const, [], {
  shape: 'agents-2',
})
// The clock the pane draws elapsed times from, ticked while an agent runs.
const now = atom({ plugin: 'agent-pane', key: 'now' } as const, 0)

const MARKS = {
  running: { glyph: '●', color: 'warning' },
  done: { glyph: '✓', color: 'success' },
  failed: { glyph: '✗', color: 'error' },
} as const

// The input fields that say what a tool call is about, most telling first.
const SUBJECTS = [
  'command',
  'file_path',
  'pattern',
  'description',
  'url',
  'query',
  'skill',
  'prompt',
] as const

const compact = (n: number): string => {
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(1)}M`
  }

  if (n >= 1_000) {
    return `${(n / 1_000).toFixed(1)}k`
  }

  return String(n)
}

const elapsed = (ms: number): string => {
  const seconds = Math.max(0, Math.round(ms / 1_000))

  if (seconds < 60) {
    return `${seconds}s`
  }

  return `${Math.floor(seconds / 60)}m${String(seconds % 60).padStart(2, '0')}s`
}

const oneLine = (text: string, limit: number): string =>
  text.replace(/\s+/g, ' ').trim().slice(0, limit)

// claude-fable-5-2-20260101 -> fable-5-2
const shortModel = (model: string): string =>
  model.replace(/^claude-/, '').replace(/-\d{8}$/, '')

// A wide character (CJK, emoji) takes two terminal cells.
const cellsOf = (char: string): number =>
  (char.codePointAt(0) ?? 0) > 0x2e7f ? 2 : 1

// Cuts `text` to what fits in `cells` terminal cells.
const fit = (text: string, cells: number): string => {
  let used = 0
  let out = ''

  for (const char of text) {
    used += cellsOf(char)

    if (used > cells) {
      return `${out.slice(0, -1)}…`
    }

    out += char
  }

  return out
}

const rowsOf = (text: string, columns: number): number => {
  let used = 0

  for (const char of text) {
    used += cellsOf(char)
  }

  return Math.max(1, Math.ceil(used / Math.max(1, columns)))
}

// `Bash: npm test`, `Read: /src/app.ts`, or the tool's name alone.
const describe = (tool: string, input: Record<string, unknown>): string => {
  for (const key of SUBJECTS) {
    const value = input[key]

    if (typeof value === 'string' && value.trim() !== '') {
      return oneLine(`${tool}: ${value}`, ACTIVITY_CHARS)
    }
  }

  return tool
}

let ticker: { cancel: () => void } | null = null

const patch = (
  $: EngineInterface,
  id: string,
  change: (row: AgentRow) => AgentRow,
): Promise<unknown> =>
  update($, agents, list =>
    list.map(row => (row.id === id ? change(row) : row)),
  )

// Ticks once a second while any agent runs, and stops itself when none does.
const tick = ($: EngineInterface): void => {
  if (ticker !== null) {
    return
  }

  ticker = $.clock.every(1_000, () => {
    void (async () => {
      const list = await read($, agents)

      if (list.some(row => row.status === 'running')) {
        const at = await $.clock.now()
        await update($, now, () => at)
      } else {
        ticker?.cancel()
        ticker = null
      }
    })().catch(() => {})
  })
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'agent-pane',
      description: "Show or hide the pane of this session's subagents",
    })

    return next(e)
  })

  // A toggle: the command closes the pane when it is open.
  on('command.run', { command: 'agent-pane' }, async $ => {
    const isOpen = (await $.ui.panes()).some(pane => pane.id === PANE)

    if (isOpen) {
      await $.ui.close({ id: PANE })

      return { text: 'Agents pane closed.' }
    }

    await $.ui.open({ id: PANE, title: TITLE })

    return { text: 'Agents pane opened.' }
  })

  on('agent.spawn', async ($, e, next) => {
    const spawned = await next(e)

    // The pane must never cost a spawn its result.
    try {
      if (spawned.deny === undefined && spawned.agentId !== undefined) {
        const at = await $.clock.now()
        const row: AgentRow = {
          id: spawned.agentId,
          type: e.subagentType,
          description: e.description,
          model: spawned.model,
          status: 'running',
          startedAt: at,
          endedAt: null,
          tools: 0,
          activity: null,
          report: null,
          contextTokens: 0,
        }
        await update($, agents, list =>
          [...list.filter(one => one.id !== row.id), row].slice(-KEPT),
        )
        await update($, now, () => at)
        tick($)
        void $.ui.open({ id: PANE, title: TITLE }).catch(() => {})
      }
    } catch {
      // The agent runs unlisted.
    }

    return spawned
  })

  on('turn.start', async ($, e, next) => {
    const { agentId } = e

    if (agentId !== undefined) {
      try {
        // A finished agent that is sent a message runs again.
        await patch($, agentId, row => ({
          ...row,
          status: 'running',
          endedAt: null,
          report: null,
        }))
        tick($)
      } catch {
        // The row keeps its last state.
      }
    }

    return next(e)
  })

  // Each model request of an agent reports the size of its context.
  on('turn.step', async function* ($, e, next) {
    const response = yield* next(e)
    const { agentId } = e

    if (agentId !== undefined && response.usage !== null) {
      try {
        const size =
          response.usage.input_tokens +
          response.usage.output_tokens +
          response.usage.cache_read_input_tokens +
          response.usage.cache_creation_input_tokens
        await patch($, agentId, row => ({ ...row, contextTokens: size }))
      } catch {
        // The row keeps its last figure.
      }
    }

    return response
  })

  on('tool.call', async ($, e, next) => {
    const { agentId } = e

    if (agentId !== undefined) {
      try {
        const activity = describe(
          String(e.tool),
          e as unknown as Record<string, unknown>,
        )
        await patch($, agentId, row => ({
          ...row,
          tools: row.tools + 1,
          activity,
        }))
      } catch {
        // The count misses one call.
      }
    }

    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    const { agentId } = e

    if (agentId !== undefined) {
      try {
        const at = await $.clock.now()
        const report = oneLine(e.answer, REPORT_CHARS)
        await patch($, agentId, row => ({
          ...row,
          status: e.reason === 'answer' ? 'done' : 'failed',
          endedAt: at,
          activity: null,
          report: report === '' ? `(${e.reason})` : report,
        }))
      } catch {
        // The row keeps its last state.
      }
    }

    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const list = await read($, agents)
    const at = await read($, now)
    const columns = Math.max(20, e.props.bodyColumns)
    const detailColumns = columns - 4
    const running = list.filter(row => row.status === 'running')
    const finished = list.filter(row => row.status !== 'running')
    // Running agents first, then the latest to finish.
    const ordered = [
      ...running.reverse(),
      ...finished.sort((a, b) => (b.endedAt ?? 0) - (a.endedAt ?? 0)),
    ]

    // Fills the body's rows: one for the summary, one kept for `n more`.
    const room = Math.max(4, e.props.scroll.bodyRows) - 2
    const shown: { row: AgentRow; detail: string | null }[] = []
    let used = 0

    for (const row of ordered) {
      const detail =
        row.status === 'running'
          ? row.activity === null
            ? null
            : fit(row.activity, detailColumns)
          : row.report === null
            ? null
            : fit(row.report, detailColumns * REPORT_ROWS - 1)
      const height =
        2 + (detail === null ? 0 : rowsOf(detail, detailColumns))

      if (used + height > room && shown.length > 0) {
        break
      }

      shown.push({ row, detail })
      used += height
    }

    return (
      <Box flexDirection="column">
        <Text dimColor>
          {running.length} running · {finished.length} finished
        </Text>
        {list.length === 0 && <Text dimColor>No subagents yet.</Text>}
        {shown.map(({ row, detail }) => {
          const mark = MARKS[row.status]
          const span =
            (row.endedAt ?? Math.max(at, row.startedAt)) - row.startedAt

          return (
            <Box flexDirection="column">
              <Text wrap="truncate-end">
                <Text color={mark.color}>{mark.glyph}</Text>{' '}
                <Text weight="bold">{row.type}</Text> {row.description}
              </Text>
              <Text dimColor wrap="truncate-end">
                {'  '}
                {elapsed(span)} · {row.tools} tools
                {row.contextTokens > 0
                  ? ` · ctx ${compact(row.contextTokens)}`
                  : ''}
                {' · '}
                {shortModel(row.model)}
              </Text>
              {detail !== null && (
                <Box flexDirection="row">
                  <Text dimColor>
                    {'  '}
                    {row.status === 'running' ? '▸ ' : '⎿ '}
                  </Text>
                  <Box flexDirection="column" width={detailColumns}>
                    <Text
                      wrap="wrap"
                      color={row.status === 'failed' ? 'error' : undefined}
                      dimColor={row.status === 'running'}
                    >
                      {detail}
                    </Text>
                  </Box>
                </Box>
              )}
            </Box>
          )
        })}
        {list.length > shown.length && (
          <Text dimColor>… {list.length - shown.length} more</Text>
        )}
      </Box>
    )
  })
}
