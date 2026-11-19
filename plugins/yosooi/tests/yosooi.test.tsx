import type { On } from 'claude-code'
import { expect, test } from 'claude-code/testing'

const row = { plugin: 'yosooi', surface: 'terminal', requestId: 'r1' } as const

// Stands for the engine beneath the mod: its own row is the word `engine`.
const engine = (on: On) => {
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)

    return <Text>engine</Text>
  })
}

test('a prompt and a reply get a heading over the engine row', async ($, on) => {
  engine(on)

  const user = await $.ui.mount({
    ...row,
    component: 'UserMessage',
    viewport: { columns: 60, rows: 24 },
    props: { text: 'hi', origin: { kind: 'composer' }, isExpanded: false },
  })
  expect((await user.find({ type: 'Text', text: /YOU/ }))?.text).toContain('━')
  expect(await user.find({ type: 'Text', text: /^engine$/ })).toBeDefined()
  await user.unmount()

  const reply = await $.ui.mount({
    ...row,
    component: 'AssistantMessage',
    props: { text: 'hello', isFirstOfReply: true },
  })
  expect(await reply.find({ type: 'Text', text: /CLAUDE/ })).toBeDefined()
  await reply.unmount()

  const later = await $.ui.mount({
    ...row,
    component: 'AssistantMessage',
    props: { text: 'more', isFirstOfReply: false },
  })
  expect(await later.find({ type: 'Text', text: /CLAUDE/ })).toBeUndefined()
  await later.unmount()
})

test('a known tool draws a chip, any other keeps the engine row', async ($, on) => {
  engine(on)

  const call = {
    tool_use_id: 'r1',
    isRunning: false,
    isErrored: false,
    isInterrupted: false,
  }
  const bash = await $.ui.mount({
    ...row,
    component: 'ToolUse',
    props: { ...call, tool: 'Bash', input: { command: 'ls\n  -la' } },
  })
  expect(await bash.find({ type: 'Text', text: / BASH / })).toBeDefined()
  expect(await bash.find({ type: 'Text', text: /ls -la/ })).toBeDefined()
  expect(await bash.find({ type: 'Text', text: /^engine$/ })).toBeUndefined()
  await bash.unmount()

  const agent = await $.ui.mount({
    ...row,
    component: 'ToolUse',
    props: { ...call, tool: 'Agent', input: { prompt: 'x' } },
  })
  expect(await agent.find({ type: 'Text', text: /^engine$/ })).toBeDefined()
  await agent.unmount()

  const group = await $.ui.mount({
    ...row,
    component: 'ToolGroup',
    props: {
      isActive: false,
      isExpanded: false,
      isCallsOnly: true,
      calls: [
        { ...call, tool: 'Read', input: { file_path: '/a/b/c/d.ts' } },
        { ...call, tool: 'Read', input: { file_path: '/a/e.ts' } },
      ],
    },
  })
  expect(await group.find({ type: 'Text', text: /READ ×2/ })).toBeDefined()
  await group.unmount()
})

test('the spinner and the closing line draw', async ($, on) => {
  engine(on)
  on('clock.every', () => ({ value: undefined }))

  const spinner = await $.ui.mount({
    ...row,
    component: 'Spinner',
    props: { word: 'Baking', message: null, suffix: '…', mode: 'thinking' },
  })
  expect(await spinner.find({ type: 'Text', text: /━/ })).toBeDefined()
  expect(await spinner.find({ type: 'Text', text: /^engine$/ })).toBeDefined()
  await spinner.unmount()

  const closing = { word: 'Baked', durationMs: 64_000 }
  const done = await $.ui.mount({
    ...row,
    component: 'TurnDuration',
    viewport: { columns: 60, rows: 24 },
    props: closing,
  })
  expect((await done.find({ type: 'Text', text: /Baked/ }))?.text).toContain(
    'Baked for 1m 4s',
  )
  await done.unmount()

})

test('/yosooi off hands every row back to the engine', async ($, on) => {
  engine(on)
  on('store.set', () => ({ value: undefined }))

  await $.command.run({
    command: 'yosooi',
    args: 'off',
    origin: { kind: 'composer' },
    presentation: { isFullscreen: false, columns: 80 },
  })
  const off = await $.ui.mount({
    ...row,
    component: 'TurnDuration',
    props: { word: 'Baked', durationMs: 64_000 },
  })
  expect((await off.find({ type: 'Text' }))?.text).toBe('engine')
  await off.unmount()
})
