import type { PaletteName } from '../types'

export type Palette = {
  // The gradient every rule and sweep runs through, left to right.
  stops: readonly string[]
  // Chip backgrounds by what a tool does.
  exec: string
  read: string
  write: string
  other: string
  ok: string
  error: string
  // Text drawn on a chip.
  ink: string
}

export const PALETTES: Record<Exclude<PaletteName, 'off'>, Palette> = {
  neon: {
    stops: ['#ff2bd6', '#8a5cff', '#00e5ff'],
    exec: '#ffb454',
    read: '#00e5ff',
    write: '#7dff9b',
    other: '#b69cff',
    ok: '#7dff9b',
    error: '#ff5370',
    ink: '#0b0b14',
  },
  akane: {
    stops: ['#ffd166', '#ff7a45', '#e0245e'],
    exec: '#ffd166',
    read: '#ff9e7a',
    write: '#f2e9a0',
    other: '#f08fb0',
    ok: '#f2e9a0',
    error: '#ff4d5e',
    ink: '#1a0d0a',
  },
  wakaba: {
    stops: ['#d9ff8a', '#3ddc84', '#00a8a8'],
    exec: '#f0d264',
    read: '#5fd7c7',
    write: '#a6f070',
    other: '#9ad0a0',
    ok: '#a6f070',
    error: '#ff6b6b',
    ink: '#07140c',
  },
  koori: {
    stops: ['#e6f7ff', '#7ab8ff', '#6a6cff'],
    exec: '#ffd9a0',
    read: '#9fd8ff',
    write: '#b8f2e6',
    other: '#b9b6ff',
    ok: '#b8f2e6',
    error: '#ff7a90',
    ink: '#0a0f1c',
  },
}

export const PALETTE_NAMES = Object.keys(PALETTES) as Exclude<
  PaletteName,
  'off'
>[]

export const isPaletteName = (value: unknown): value is PaletteName =>
  value === 'off' ||
  (typeof value === 'string' && (PALETTE_NAMES as string[]).includes(value))

const channel = (hex: string, at: number): number =>
  parseInt(hex.slice(at, at + 2), 16)

const two = (n: number): string => Math.round(n).toString(16).padStart(2, '0')

// The color a fraction `t` (0 to 1) of the way along the stops.
export const along = (stops: readonly string[], t: number): string => {
  const clamped = Math.min(1, Math.max(0, t))
  const scaled = clamped * (stops.length - 1)
  const i = Math.min(stops.length - 2, Math.floor(scaled))
  const from = stops[i] ?? '#ffffff'
  const to = stops[i + 1] ?? from
  const f = scaled - i
  const mix = (at: number): string =>
    two(channel(from, at) + (channel(to, at) - channel(from, at)) * f)

  return `#${mix(1)}${mix(3)}${mix(5)}`
}

// `text` cut into runs of one color each, at most `maxRuns` of them, so a
// rule as wide as the terminal stays a small tree.
export const runs = (
  text: string,
  stops: readonly string[],
  maxRuns = 32,
): { text: string; color: string }[] => {
  const chars = [...text]
  const size = Math.max(1, Math.ceil(chars.length / maxRuns))
  const out: { text: string; color: string }[] = []

  for (let i = 0; i < chars.length; i += size) {
    out.push({
      text: chars.slice(i, i + size).join(''),
      color: along(stops, chars.length <= 1 ? 0 : i / (chars.length - 1)),
    })
  }

  return out
}
