import { atom, memberOf, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Run } from '../types'

// One member per Bash call, keyed by its tool_use_id (a row's requestId).
const runs = atom({ plugin: 'bash-meter', key: 'runs' } as const, null)

const EXIT_CODE = /Exit code (\d+)/

const duration = (ms: number): string => {
  if (ms < 1_000) {
    return `${Math.round(ms)}ms`
  }

  if (ms < 60_000) {
    return `${(ms / 1_000).toFixed(1)}s`
  }

  return `${Math.floor(ms / 60_000)}m${Math.round((ms % 60_000) / 1_000)}s`
}

// A command as one short line, for a summary row.
const brief = (command: string): string => {
  const line = command.replace(/\s+/g, ' ').trim()

  return line.length > 48 ? `${line.slice(0, 47)}…` : line
}

// A call's own execution time as the engine reports it to the settings hooks,
// which leaves out the permission check and the hooks' own time. Held only
// from that report to the end of the same call.
const executed = new Map<string, number>()

export const register: Register = on => {
  on('classic.PostToolUse', ($, e, next) => {
    if (e.tool_name === 'Bash' && e.duration_ms !== undefined) {
      executed.set(e.tool_use_id, e.duration_ms)
    }

    return next(e)
  })

  on('classic.PostToolUseFailure', ($, e, next) => {
    if (e.tool_name === 'Bash' && e.duration_ms !== undefined) {
      executed.set(e.tool_use_id, e.duration_ms)
    }

    return next(e)
  })

  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const startedAt = await $.clock.now()
    const ran = await next(e)

    // The meter must never cost the call its result.
    try {
      const hasFailed = ran.deny !== undefined || ran.isError === true
      const code = EXIT_CODE.exec(ran.text ?? '')?.[1]
      const record = ran.result as { backgroundTaskId?: string } | undefined
      // The engine's figure where it gave one; else the whole call's time,
      // which also counts the permission check and the settings hooks.
      const own = executed.get(e.tool_use_id)
      executed.delete(e.tool_use_id)
      const run: Run = {
        ms: own ?? (await $.clock.now()) - startedAt,
        exitCode: hasFailed && code !== undefined ? Number(code) : null,
        hasFailed,
        isBackground: record?.backgroundTaskId !== undefined,
      }
      await update(
        $,
        memberOf(runs, { requestId: e.tool_use_id }),
        () => run,
      )
    } catch {
      // The row draws without its meter.
    }

    return ran
  })

  // The transcript folds a run of calls into one count line (`ran 3 shell
  // commands`), where no Bash row is drawn: the meter goes under that line.
  on('ui.render', { component: 'ToolGroup' }, async ($, e, next) => {
    if (e.props.isExpanded) {
      return next(e)
    }

    const timed: { run: Run; command: string }[] = []

    for (const call of e.props.calls) {
      if (call.tool !== 'Bash' || call.tool_use_id === undefined) {
        continue
      }

      const run = await read($, memberOf(runs, { requestId: call.tool_use_id }))

      if (run !== null) {
        const input = call.input as { command?: unknown } | null
        const command = typeof input?.command === 'string' ? input.command : ''
        timed.push({ run, command: brief(command) })
      }
    }

    if (timed.length === 0) {
      return next(e)
    }

    const { Box, Text } = $.ui.resolve(e)
    const total = timed.reduce((sum, one) => sum + one.run.ms, 0)
    const slowest = timed.reduce((a, b) => (b.run.ms > a.run.ms ? b : a))
    const failed = timed.filter(one => one.run.hasFailed)

    return (
      <Box flexDirection="column">
        {await next(e)}
        <Text dimColor wrap="truncate-end">
          {'  '}⏱ {timed.length} bash · {duration(total)}
          {timed.length > 1 && slowest.run.ms >= 1_000
            ? ` · slowest ${duration(slowest.run.ms)} (${slowest.command})`
            : ''}
        </Text>
        {failed.map(one => (
          <Text color="error" wrap="truncate-end">
            {'  '}✗{' '}
            {one.run.exitCode === null ? 'failed' : `exit ${one.run.exitCode}`}{' '}
            · {duration(one.run.ms)} · {one.command}
          </Text>
        ))}
      </Box>
    )
  })

  on(
    'ui.render',
    { component: 'ToolUse', props: { tool: 'Bash' } },
    async ($, e, next) => {
      const run = await read($, memberOf(runs, e))

      if (run === null) {
        return next(e)
      }

      const { Box, Text } = $.ui.resolve(e)

      return (
        <Box flexDirection="row" columnGap={1}>
          {await next(e)}
          <Box flexShrink={0}>
            {run.hasFailed ? (
              <Text color="error">
                ✗ {run.exitCode === null ? 'failed' : `exit ${run.exitCode}`} ·{' '}
                {duration(run.ms)}
              </Text>
            ) : (
              <Text dimColor>
                {run.isBackground ? '→ background' : duration(run.ms)}
              </Text>
            )}
          </Box>
        </Box>
      )
    },
  )
}
