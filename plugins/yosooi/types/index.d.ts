export type PaletteName = 'neon' | 'akane' | 'wakaba' | 'koori' | 'off'

declare module 'claude-code' {
  interface PluginState {
    yosooi: {
      // The palette in force; `off` hands every row back to the engine.
      palette: PaletteName
      // The spinner's animation frame, written by a timer while it is drawn.
      frame: number
    }
  }
}
