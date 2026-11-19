import { atom, read, update } from 'claude-code'
import type { ElementTable, Register, Timer } from 'claude-code'

import type { PaletteName } from '../types'
import {
  PALETTES,
  PALETTE_NAMES,
  along,
  isPaletteName,
  runs,
  type Palette,
} from './palette'

type Table = ElementTable<'terminal'>

const STORE_KEY = 'palette'
const paletteName = atom(
  { plugin: 'yosooi', key: 'palette' } as const,
  'neon' as PaletteName,
)
const frame = atom({ plugin: 'yosooi', key: 'frame' } as const, 0)

// Tools whose row the mod draws itself, by what they do. Any other tool
// (an agent, a question, a plan) keeps the engine's row, which shows more
// than one line could.
const KINDS: Record<string, 'exec' | 'read' | 'write' | 'other'> = {
  Bash: 'exec',
  Read: 'read',
  Grep: 'read',
  Glob: 'read',
  WebFetch: 'read',
  WebSearch: 'read',
  ToolSearch: 'read',
  Edit: 'write',
  Write: 'write',
  NotebookEdit: 'write',
  Skill: 'other',
}

const RULE_MAX = 96
const FADE = '╍╍╍┅┅┅┉┉┉'

const oneLine = (value: unknown): string =>
  typeof value === 'string' ? value.replace(/\s+/g, ' ').trim() : ''

const shortPath = (value: unknown): string => {
  const path = oneLine(value)
  const parts = path.split('/').filter(Boolean)

  return parts.length > 3 ? `…/${parts.slice(-2).join('/')}` : path
}

// A tool call as a chip label and one line of what it was asked.
const describe = (
  tool: string,
  input: unknown,
): { label: string; kind: keyof typeof KIND_COLOR; summary: string } | null => {
  const given = (input ?? {}) as Record<string, unknown>

  if (tool.startsWith('mcp__')) {
    const [, server = '', ...name] = tool.split('__')
    const first = Object.values(given).find(v => typeof v === 'string')

    return {
      label: 'MCP',
      kind: 'other',
      summary: `${server} › ${name.join('__')}${first === undefined ? '' : `  ${oneLine(first)}`}`,
    }
  }

  const kind = KINDS[tool]

  if (kind === undefined) {
    return null
  }

  const summary =
    tool === 'Bash'
      ? oneLine(given.command)
      : tool === 'Grep'
        ? `${oneLine(given.pattern)}${given.path === undefined ? '' : `  in ${shortPath(given.path)}`}`
        : tool === 'Glob'
          ? oneLine(given.pattern)
          : tool === 'WebFetch'
            ? oneLine(given.url)
            : tool === 'WebSearch' || tool === 'ToolSearch'
              ? oneLine(given.query)
              : tool === 'Skill'
                ? `${oneLine(given.skill)} ${oneLine(given.args)}`.trim()
                : shortPath(given.file_path ?? given.notebook_path)

  return { label: tool.toUpperCase(), kind, summary }
}

const KIND_COLOR = {
  exec: (p: Palette) => p.exec,
  read: (p: Palette) => p.read,
  write: (p: Palette) => p.write,
  other: (p: Palette) => p.other,
}

const duration = (ms: number): string => {
  const seconds = Math.round(ms / 1_000)

  return seconds < 60
    ? `${seconds}s`
    : `${Math.floor(seconds / 60)}m ${seconds % 60}s`
}

const ruleWidth = (columns: number | undefined, taken: number): number =>
  Math.max(4, Math.min(RULE_MAX, (columns ?? 80) - 4) - taken)

// A chip and a rule that runs the gradient away from it and fades out.
const heading = (
  { Text }: Table,
  label: string,
  palette: Palette,
  columns: number | undefined,
  isReversed: boolean,
) => {
  const stops = isReversed ? [...palette.stops].reverse() : palette.stops
  const chip = ` ${label} `
  const width = ruleWidth(columns, chip.length + 1)
  const rule = `${'━'.repeat(Math.max(0, width - FADE.length))}${FADE}`

  return (
    <Text wrap="truncate-end">
      <Text backgroundColor={stops[0]} color={palette.ink} bold>
        {chip}
      </Text>{' '}
      {runs(rule, stops).map(run => (
        <Text color={run.color}>{run.text}</Text>
      ))}
    </Text>
  )
}

// The palette in force, or null while the mod is switched off.
async function current(
  $: Parameters<typeof read>[0],
): Promise<Palette | null> {
  const name = await read($, paletteName)

  return name === 'off' ? null : PALETTES[name]
}

export const register: Register = on => {
  let ticker: Timer | undefined
  let spinnerSeenAt = 0

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'yosooi',
      description: 'トランスクリプトの配色を切り替える',
      argumentHint: `[${PALETTE_NAMES.join('|')}|off]`,
    })
    const stored = await $.store.get(STORE_KEY)

    if (isPaletteName(stored)) {
      await update($, paletteName, () => stored)
    }

    return next(e)
  })

  on('command.run', { command: 'yosooi' }, async ($, e) => {
    const asked = e.args.trim().toLowerCase()

    if (asked === '') {
      return {
        text: `yosooi: ${await read($, paletteName)}（選べる配色: ${PALETTE_NAMES.join(', ')}, off）`,
      }
    }

    if (!isPaletteName(asked)) {
      return {
        text: `yosooi: 「${asked}」という配色はない。${PALETTE_NAMES.join(', ')}, off から選ぶ。`,
      }
    }

    await update($, paletteName, () => asked)
    await $.store.set(STORE_KEY, asked)

    return { text: `yosooi: ${asked}` }
  })

  on('ui.render', { component: 'UserMessage' }, async ($, e, next) => {
    if (
      e.surface !== 'terminal' ||
      e.props.isExpanded ||
      e.props.origin.kind !== 'composer'
    ) {
      return next(e)
    }

    const palette = await current($)

    if (palette === null) {
      return next(e)
    }

    const table = $.ui.resolve(e)
    const { Box } = table

    return (
      <Box flexDirection="column" marginTop={1}>
        {heading(table, '❯ YOU', palette, e.viewport?.columns, false)}
        {await next(e)}
      </Box>
    )
  })

  on('ui.render', { component: 'AssistantMessage' }, async ($, e, next) => {
    if (
      e.surface !== 'terminal' ||
      !e.props.isFirstOfReply ||
      e.props.isSummary
    ) {
      return next(e)
    }

    const palette = await current($)

    if (palette === null) {
      return next(e)
    }

    const table = $.ui.resolve(e)
    const { Box } = table

    return (
      <Box flexDirection="column" marginTop={1}>
        {heading(table, '✦ CLAUDE', palette, e.viewport?.columns, true)}
        {await next(e)}
      </Box>
    )
  })

  on('ui.render', { component: 'ToolUse' }, async ($, e, next) => {
    if (e.surface !== 'terminal' || e.props.isExpanded) {
      return next(e)
    }

    const call = describe(e.props.tool, e.props.input)
    const palette = await current($)

    if (call === null || palette === null) {
      return next(e)
    }

    const { Box, Text } = $.ui.resolve(e)
    const { isRunning, isErrored, isInterrupted } = e.props
    const mark = isInterrupted ? '⊘' : isErrored ? '✗' : isRunning ? '◌' : '●'
    const markColor =
      isErrored || isInterrupted
        ? palette.error
        : isRunning
          ? palette.stops[0]
          : palette.ok

    return (
      <Box flexDirection="row" columnGap={1}>
        <Box flexShrink={0}>
          <Text color={markColor}>{mark}</Text>
        </Box>
        <Box flexShrink={0}>
          <Text
            backgroundColor={KIND_COLOR[call.kind](palette)}
            color={palette.ink}
            bold
          >
            {` ${call.label} `}
          </Text>
        </Box>
        <Text wrap="truncate-end" dimColor={!isRunning}>
          {call.summary}
          {isInterrupted ? '  interrupted' : ''}
        </Text>
      </Box>
    )
  })

  // A folded run of calls (`Read 3 files, ran 2 shell commands`) as one chip
  // per tool with its count, and the call in hand while the run is live.
  on('ui.render', { component: 'ToolGroup' }, async ($, e, next) => {
    if (
      e.surface !== 'terminal' ||
      e.props.isExpanded ||
      e.props.isCallsOnly !== true
    ) {
      return next(e)
    }

    const palette = await current($)
    const calls = e.props.calls.map(call => describe(call.tool, call.input))

    if (palette === null || calls.length === 0 || calls.includes(null)) {
      return next(e)
    }

    const counts = new Map<string, { kind: keyof typeof KIND_COLOR; n: number }>()

    for (const call of calls) {
      if (call !== null) {
        const seen = counts.get(call.label)
        counts.set(call.label, { kind: call.kind, n: (seen?.n ?? 0) + 1 })
      }
    }

    const { Box, Text } = $.ui.resolve(e)
    const last = calls[calls.length - 1]
    const { isActive } = e.props

    return (
      <Box flexDirection="row" columnGap={1}>
        <Box flexShrink={0}>
          <Text color={isActive ? palette.stops[0] : palette.ok}>
            {isActive ? '◌' : '●'}
          </Text>
        </Box>
        {[...counts].map(([label, { kind, n }]) => (
          <Box flexShrink={0}>
            <Text
              backgroundColor={KIND_COLOR[kind](palette)}
              color={palette.ink}
              bold
            >
              {` ${label}${n > 1 ? ` ×${n}` : ''} `}
            </Text>
          </Box>
        ))}
        <Text wrap="truncate-end" dimColor>
          {isActive || calls.length === 1 ? (last?.summary ?? '') : ''}
        </Text>
      </Box>
    )
  })

  // A comet running the gradient beside the engine's own line, which keeps
  // its word, time and token count.
  on('ui.render', { component: 'Spinner' }, async ($, e, next) => {
    if (e.surface !== 'terminal') {
      return next(e)
    }

    const palette = await current($)

    if (palette === null) {
      return next(e)
    }

    // The timer lives only while a spinner is being drawn: each tick redraws
    // this hook, and two seconds with no redraw ends it.
    spinnerSeenAt = Date.now()
    ticker ??= $.clock.every(150, () => {
      if (Date.now() - spinnerSeenAt > 2_000) {
        ticker?.cancel()
        ticker = undefined

        return
      }

      void update($, frame, n => (n + 1) % 3_600).catch(() => undefined)
    })

    const { Box, Text } = $.ui.resolve(e)
    const cells = 8
    const tail = 4
    const head = (await read($, frame)) % (cells + tail)

    return (
      <Box flexDirection="row" columnGap={1}>
        {/* The engine's line sits under a blank row of its own. */}
        <Box flexShrink={0} marginTop={1}>
          <Text>
            {Array.from({ length: cells }, (_, i) => {
              const behind = head - i

              return behind >= 0 && behind < tail ? (
                <Text color={along(palette.stops, behind / (tail - 1))}>━</Text>
              ) : (
                <Text dimColor>╌</Text>
              )
            })}
          </Text>
        </Box>
        {await next(e)}
      </Box>
    )
  })

  // The turn's closing line as a rule across the transcript.
  on('ui.render', { component: 'TurnDuration' }, async ($, e, next) => {
    if (
      e.surface !== 'terminal' ||
      e.props.isExpanded ||
      e.props.waitingFor !== undefined
    ) {
      return next(e)
    }

    const palette = await current($)

    if (palette === null) {
      return next(e)
    }

    const { Text } = $.ui.resolve(e)
    const words = ` ✦ ${e.props.word} for ${duration(e.props.durationMs)} `
    const side = Math.floor(ruleWidth(e.viewport?.columns, words.length) / 2)
    const left = `${[...FADE].reverse().join('')}${'━'.repeat(Math.max(0, side - FADE.length))}`
    const right = `${'━'.repeat(Math.max(0, side - FADE.length))}${FADE}`

    return (
      <Text wrap="truncate-end">
        {runs(`${left}${words}${right}`, palette.stops, 48).map(run => (
          <Text color={run.color}>{run.text}</Text>
        ))}
      </Text>
    )
  })
}
